import uuid

from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.media.contracts.repositories.media_file import (
    AbstractMediaFileRepository,
)
from app.modules.media.enums import MediaFileRole
from app.modules.media.models.media_file import MediaFile


class MediaFileRepository(
    BaseRepository[MediaFile],
    AbstractMediaFileRepository,
):
    def create(self, media_file: MediaFile) -> MediaFile:
        self.session.add(media_file)
        return media_file

    async def get_by_id(self, media_file_id: uuid.UUID) -> MediaFile | None:
        statement = select(MediaFile).where(
            MediaFile.id == media_file_id
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_asset_and_role(
        self,
        media_asset_id: uuid.UUID,
        file_role: MediaFileRole,
    ) -> MediaFile | None:
        statement = select(MediaFile).where(
            MediaFile.media_asset_id == media_asset_id,
            MediaFile.file_role == file_role,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_asset_id(
        self,
        media_asset_id: uuid.UUID,
    ) -> list[MediaFile]:
        statement = (
            select(MediaFile)
            .where(MediaFile.media_asset_id == media_asset_id)
            .order_by(MediaFile.created_at)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())