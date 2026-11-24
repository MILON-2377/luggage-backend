import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.media.enums import MediaFileRole
from app.modules.media.models.media_file import MediaFile


class AbstractMediaFileRepository(AbstractRepository):
    @abstractmethod
    def create(self, media_file: MediaFile) -> MediaFile:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, media_file_id: uuid.UUID) -> MediaFile | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_asset_and_role(
        self,
        media_asset_id: uuid.UUID,
        file_role: MediaFileRole,
    ) -> MediaFile | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_asset_id(
        self,
        media_asset_id: uuid.UUID,
    ) -> list[MediaFile]:
        raise NotImplementedError
