import uuid

from sqlalchemy import func, select, update

from app.core.database.repositories.base import BaseRepository
from app.modules.media.contracts.repositories.media_storage_location import (
    AbstractMediaStorageLocationRepository,
)
from app.modules.media.enums import StorageLocationStatus, StorageProvider
from app.modules.media.models.media_file import MediaFile
from app.modules.media.models.media_storage_location import MediaStorageLocation


class MediaStorageLocationRepository(
    BaseRepository[MediaStorageLocation],
    AbstractMediaStorageLocationRepository,
):
    def create(self, location: MediaStorageLocation) -> MediaStorageLocation:
        self.session.add(location)
        return location

    async def get_by_id(
        self,
        location_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> MediaStorageLocation | None:
        statement = select(MediaStorageLocation).where(
            MediaStorageLocation.id == location_id
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_primary_by_file_id(
        self,
        media_file_id: uuid.UUID,
    ) -> MediaStorageLocation | None:
        statement = select(MediaStorageLocation).where(
            MediaStorageLocation.media_file_id == media_file_id,
            MediaStorageLocation.is_primary.is_(True),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_object(
        self,
        *,
        storage_provider: StorageProvider,
        storage_bucket: str | None,
        storage_key: str,
    ) -> MediaStorageLocation | None:
        statement = select(MediaStorageLocation).where(
            MediaStorageLocation.storage_provider == storage_provider,
            func.coalesce(MediaStorageLocation.storage_bucket, "")
            == (storage_bucket or ""),
            MediaStorageLocation.storage_key == storage_key,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_file_id(
        self,
        media_file_id: uuid.UUID,
    ) -> list[MediaStorageLocation]:
        statement = (
            select(MediaStorageLocation)
            .where(MediaStorageLocation.media_file_id == media_file_id)
            .order_by(MediaStorageLocation.created_at)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_asset_id(
        self,
        media_asset_id: uuid.UUID,
        *,
        status: StorageLocationStatus | None = None,
    ) -> list[MediaStorageLocation]:
        statement = (
            select(MediaStorageLocation)
            .join(
                MediaFile,
                MediaFile.id == MediaStorageLocation.media_file_id,
            )
            .where(MediaFile.media_asset_id == media_asset_id)
            .order_by(MediaStorageLocation.created_at)
        )

        if status is not None:
            statement = statement.where(MediaStorageLocation.status == status)

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_status(
        self,
        location_id: uuid.UUID,
        status: StorageLocationStatus,
    ) -> bool:
        values: dict[str, object] = {"status": status}

        if status != StorageLocationStatus.READY:
            values["is_primary"] = False

        statement = (
            update(MediaStorageLocation)
            .where(MediaStorageLocation.id == location_id)
            .values(**values)
            .returning(MediaStorageLocation.id)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None
