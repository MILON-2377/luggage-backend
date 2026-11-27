import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database.repositories.base import BaseRepository
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.enums import MediaStatus
from app.modules.media.models.media_asset import MediaAsset
from app.modules.media.models.media_file import MediaFile


class MediaAssetRepository(
    BaseRepository[MediaAsset],
    AbstractMediaAssetRepository,
):
    def create(self, media_asset: MediaAsset) -> MediaAsset:
        self.session.add(media_asset)
        return media_asset

    async def get_by_id(
        self,
        media_asset_id: uuid.UUID,
        *,
        for_update: bool = False,
        include_deleted: bool = False,
    ) -> MediaAsset | None:
        statement = select(MediaAsset).where(MediaAsset.id == media_asset_id)

        if not include_deleted:
            statement = statement.where(MediaAsset.deleted_at.is_(None))

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id_with_files(
        self,
        media_asset_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> MediaAsset | None:
        statement = (
            select(MediaAsset)
            .options(
                selectinload(MediaAsset.files).selectinload(MediaFile.storage_locations)
            )
            .where(MediaAsset.id == media_asset_id)
        )

        if not include_deleted:
            statement = statement.where(MediaAsset.deleted_at.is_(None))

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        media_asset_id: uuid.UUID,
        status: MediaStatus,
    ) -> bool:
        if status in (MediaStatus.DELETION_PENDING, MediaStatus.DELETED):
            raise ValueError(
                "Use mark_deletion_pending/mark_deleted for deletion statuses."
            )

        statement = (
            update(MediaAsset)
            .where(
                MediaAsset.id == media_asset_id,
                MediaAsset.deleted_at.is_(None),
            )
            .values(status=status)
            .returning(MediaAsset.id)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def mark_deletion_pending(
        self,
        media_asset_id: uuid.UUID,
        *,
        deleted_at: datetime,
    ) -> bool:
        statement = (
            update(MediaAsset)
            .where(
                MediaAsset.id == media_asset_id,
                MediaAsset.deleted_at.is_(None),
            )
            .values(
                status=MediaStatus.DELETION_PENDING,
                deleted_at=deleted_at,
            )
            .returning(MediaAsset.id)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def mark_deleted(self, media_asset_id: uuid.UUID) -> bool:
        statement = (
            update(MediaAsset)
            .where(
                MediaAsset.id == media_asset_id,
                MediaAsset.status == MediaStatus.DELETION_PENDING,
            )
            .values(status=MediaStatus.DELETED)
            .returning(MediaAsset.id)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_stale_pending(
        self,
        *,
        created_before: datetime,
        limit: int = 100,
    ) -> list[MediaAsset]:
        statement = (
            select(MediaAsset)
            .where(
                MediaAsset.status == MediaStatus.PENDING,
                MediaAsset.deleted_at.is_(None),
                MediaAsset.created_at < created_before,
            )
            .order_by(MediaAsset.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_deletion_pending(
        self,
        *,
        deleted_before: datetime,
        limit: int = 100,
    ) -> list[MediaAsset]:
        statement = (
            select(MediaAsset)
            .where(
                MediaAsset.status == MediaStatus.DELETION_PENDING,
                MediaAsset.deleted_at < deleted_before,
            )
            .order_by(MediaAsset.deleted_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_ids(
        self,
        media_asset_ids: list[uuid.UUID],
        *,
        include_deleted: bool = False,
    ) -> list[MediaAsset]:
        if not media_asset_ids:
            return []

        statement = select(MediaAsset).where(
            MediaAsset.id.in_(media_asset_ids),
        )

        if not include_deleted:
            statement = statement.where(MediaAsset.deleted_at.is_(None))

        result = await self.session.execute(statement)
        return list(result.scalars().all())
