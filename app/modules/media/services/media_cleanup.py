import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.contracts.services.media import AbstractMediaService
from app.modules.media.contracts.services.media_cleanup import (
    AbstractMediaCleanupService,
)
from app.modules.media.dtos.cleanup import MediaCleanupResultDTO

logger = logging.getLogger(__name__)


class MediaCleanupService(AbstractMediaCleanupService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        media_service: AbstractMediaService,
        settings: Settings,
    ) -> None:
        self.uow = uow
        self.media_service = media_service
        self.settings = settings

    async def run(self) -> MediaCleanupResultDTO:
        now = datetime.now(UTC)
        repository = self.uow.get_repository(AbstractMediaAssetRepository)

        stale_pending = await repository.list_stale_pending(
            created_before=now
            - timedelta(seconds=self.settings.MEDIA_PENDING_UPLOAD_TTL_SECONDS),
            limit=self.settings.MEDIA_CLEANUP_BATCH_SIZE,
        )
        deletion_pending = await repository.list_deletion_pending(
            deleted_before=now
            - timedelta(seconds=self.settings.MEDIA_DELETION_RETRY_AFTER_SECONDS),
            limit=self.settings.MEDIA_CLEANUP_BATCH_SIZE,
        )

        stale_ids = [asset.id for asset in stale_pending]
        deletion_ids = [asset.id for asset in deletion_pending]

        # Release the row locks before calling the provider.
        await self.uow.commit()

        stale_deleted, stale_failed = await self._delete_all(stale_ids)
        resumed, resume_failed = await self._delete_all(deletion_ids)

        return MediaCleanupResultDTO(
            stale_pending_found=len(stale_ids),
            stale_pending_deleted=stale_deleted,
            deletion_pending_found=len(deletion_ids),
            deletion_pending_resumed=resumed,
            failed=stale_failed + resume_failed,
        )

    async def _delete_all(self, asset_ids: list[uuid.UUID]) -> tuple[int, int]:
        succeeded = 0
        failed = 0

        for asset_id in asset_ids:
            try:
                await self.media_service.delete(asset_id)
                await self.uow.commit()
                succeeded += 1
            except Exception:
                await self.uow.rollback()
                failed += 1
                logger.exception("Media cleanup failed for asset %s", asset_id)

        return succeeded, failed