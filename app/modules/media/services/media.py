import re
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import PurePath

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.storage.errors import (
    AssetVerificationError,
    MediaStorageError,
)
from app.core.contracts.storage.media import AbstractMediaStorage
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.contracts.repositories.media_file import (
    AbstractMediaFileRepository,
)
from app.modules.media.contracts.repositories.media_storage_location import (
    AbstractMediaStorageLocationRepository,
)
from app.modules.media.contracts.services.media import AbstractMediaService
from app.modules.media.dtos.upload import (
    ConfirmUploadResultDTO,
    CreateUploadDTO,
    CreateUploadResultDTO,
)
from app.modules.media.enums import (
    MediaFileRole,
    MediaStatus,
    StorageLocationStatus,
)
from app.modules.media.errors.media import (
    MediaAssetNotFoundError,
    MediaFileNotFoundError,
    MediaNotPendingError,
    MediaStorageLocationNotFoundError,
)
from app.modules.media.models.media_asset import MediaAsset
from app.modules.media.models.media_file import MediaFile
from app.modules.media.models.media_storage_location import MediaStorageLocation


def _derive_file_format(filename: str, mime_type: str) -> str:
    extension = PurePath(filename).suffix.lstrip(".").lower()
    candidate = extension or mime_type.split("/")[-1].split("+")[0]
    cleaned = re.sub(r"[^a-z0-9]", "", candidate.lower())
    return cleaned[:20] or "bin"


class MediaService(AbstractMediaService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        storage: AbstractMediaStorage,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.storage = storage
        self.settings = settings

    async def create_upload(
        self,
        payload: CreateUploadDTO,
    ) -> CreateUploadResultDTO:
        asset_repository = self.uow.get_repository(AbstractMediaAssetRepository)
        file_repository = self.uow.get_repository(AbstractMediaFileRepository)
        location_repository = self.uow.get_repository(
            AbstractMediaStorageLocationRepository
        )

        asset_id = self.id_generator.generate()
        file_id = self.id_generator.generate()
        location_id = self.id_generator.generate()
        storage_key = f"media/{asset_id}"

        signed_upload = await self.storage.create_signed_upload(
            public_id=storage_key,
            media_type=payload.media_type,
            mime_type=payload.mime_type,
            expires_in=self.settings.MEDIA_UPLOAD_EXPIRES_SECONDS,
        )

        asset_repository.create(
            MediaAsset(
                id=asset_id,
                original_filename=payload.original_filename,
                media_type=payload.media_type,
                status=MediaStatus.PENDING,
                uploaded_by=payload.uploaded_by,
            )
        )
        file_repository.create(
            MediaFile(
                id=file_id,
                media_asset_id=asset_id,
                file_role=MediaFileRole.ORIGINAL,
                file_format=_derive_file_format(
                    payload.original_filename,
                    payload.mime_type,
                ),
                mime_type=payload.mime_type,
                file_size=payload.file_size,
            )
        )
        location_repository.create(
            MediaStorageLocation(
                id=location_id,
                media_file_id=file_id,
                storage_provider=self.storage.provider,
                storage_key=storage_key,
                is_primary=False,
                status=StorageLocationStatus.PENDING,
            )
        )

        await self.uow.flush()

        return CreateUploadResultDTO(
            media_asset_id=asset_id,
            upload_url=signed_upload.upload_url,
            upload_params=signed_upload.upload_params,
        )

    async def confirm_upload(
        self,
        media_asset_id: uuid.UUID,
    ) -> ConfirmUploadResultDTO:
        asset_repository = self.uow.get_repository(AbstractMediaAssetRepository)
        file_repository = self.uow.get_repository(AbstractMediaFileRepository)
        location_repository = self.uow.get_repository(
            AbstractMediaStorageLocationRepository
        )

        asset = await asset_repository.get_by_id(media_asset_id, for_update=True)

        if asset is None:
            raise MediaAssetNotFoundError(media_asset_id)

        if asset.status != MediaStatus.PENDING:
            raise MediaNotPendingError(
                media_asset_id=media_asset_id,
                status=asset.status,
            )

        media_file = await file_repository.get_by_asset_and_role(
            asset.id,
            MediaFileRole.ORIGINAL,
        )

        if media_file is None:
            raise MediaFileNotFoundError(media_asset_id)

        locations = await location_repository.list_by_file_id(media_file.id)
        location = next(
            (
                item
                for item in locations
                if item.status == StorageLocationStatus.PENDING
            ),
            None,
        )

        if location is None:
            raise MediaStorageLocationNotFoundError(media_asset_id)

        try:
            verified = await self.storage.verify_asset(
                public_id=location.storage_key,
                media_type=asset.media_type,
                expected_mime_type=media_file.mime_type,
                expected_file_format=media_file.file_format,
            )

            if verified.file_size is None or verified.file_size <= 0:
                raise AssetVerificationError(
                    "The uploaded media asset reported an invalid file size.",
                    details={"public_id": location.storage_key},
                )
        except AssetVerificationError:
            asset.status = MediaStatus.FAILED
            location.status = StorageLocationStatus.FAILED

            # Best effort: remove the rejected file from the provider.
            with suppress(MediaStorageError):
                await self.storage.delete_asset(
                    public_id=location.storage_key,
                    media_type=asset.media_type,
                )

            await self.uow.commit()
            raise

        media_file.mime_type = verified.mime_type
        media_file.file_size = verified.file_size
        media_file.file_format = verified.file_format or media_file.file_format
        media_file.width = verified.width
        media_file.height = verified.height
        media_file.duration = (
            Decimal(str(verified.duration)) if verified.duration is not None else None
        )

        location.storage_url = verified.secure_url
        location.status = StorageLocationStatus.READY
        location.is_primary = True

        asset.status = MediaStatus.READY

        await self.uow.flush()

        return ConfirmUploadResultDTO(
            media_asset_id=asset.id,
            status=asset.status,
            media_type=asset.media_type,
            mime_type=media_file.mime_type,
            file_format=media_file.file_format,
            file_size=media_file.file_size,
            width=media_file.width,
            height=media_file.height,
            duration=media_file.duration,
            url=location.storage_url,
        )

    async def delete(self, media_asset_id: uuid.UUID) -> None:
        asset_repository = self.uow.get_repository(AbstractMediaAssetRepository)
        location_repository = self.uow.get_repository(
            AbstractMediaStorageLocationRepository
        )

        asset = await asset_repository.get_by_id(
            media_asset_id,
            for_update=True,
            include_deleted=True,
        )

        if asset is None or asset.status == MediaStatus.DELETED:
            raise MediaAssetNotFoundError(media_asset_id)

        asset_id = asset.id
        media_type = asset.media_type

        if asset.status != MediaStatus.DELETION_PENDING:
            await asset_repository.mark_deletion_pending(
                asset_id,
                deleted_at=datetime.now(UTC),
            )

        locations = await location_repository.list_by_asset_id(asset_id)
        targets = [
            location
            for location in locations
            if location.status != StorageLocationStatus.DELETED
        ]

        for location in targets:
            location.is_primary = False
            location.status = StorageLocationStatus.DELETION_PENDING

        # Capture plain values before commit so nothing depends on ORM
        # objects that a commit may expire.
        pending = [(location.id, location.storage_key) for location in targets]

        # Persist DELETION_PENDING before touching the provider, so a provider
        # failure leaves a retryable state instead of rolling everything back.
        await self.uow.commit()

        for location_id, storage_key in pending:
            await self.storage.delete_asset(
                public_id=storage_key,
                media_type=media_type,
            )
            await location_repository.update_status(
                location_id,
                StorageLocationStatus.DELETED,
            )

        await asset_repository.mark_deleted(asset_id)
        await self.uow.flush()
