import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.media.enums import StorageLocationStatus, StorageProvider
from app.modules.media.models.media_storage_location import MediaStorageLocation


class AbstractMediaStorageLocationRepository(AbstractRepository):
    @abstractmethod
    def create(self, location: MediaStorageLocation) -> MediaStorageLocation:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        location_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> MediaStorageLocation | None:
        raise NotImplementedError

    @abstractmethod
    async def get_primary_by_file_id(
        self,
        media_file_id: uuid.UUID,
    ) -> MediaStorageLocation | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_object(
        self,
        *,
        storage_provider: StorageProvider,
        storage_bucket: str | None,
        storage_key: str,
    ) -> MediaStorageLocation | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_file_id(
        self,
        media_file_id: uuid.UUID,
    ) -> list[MediaStorageLocation]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_asset_id(
        self,
        media_asset_id: uuid.UUID,
        *,
        status: StorageLocationStatus | None = None,
    ) -> list[MediaStorageLocation]:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        location_id: uuid.UUID,
        status: StorageLocationStatus,
    ) -> bool:
        raise NotImplementedError
