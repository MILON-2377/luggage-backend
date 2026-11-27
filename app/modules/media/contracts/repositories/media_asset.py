import uuid
from abc import abstractmethod
from datetime import datetime

from app.core.contracts.database.repository import AbstractRepository
from app.modules.media.enums import MediaStatus
from app.modules.media.models.media_asset import MediaAsset


class AbstractMediaAssetRepository(AbstractRepository):
    @abstractmethod
    def create(self, media_asset: MediaAsset) -> MediaAsset:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        media_asset_id: uuid.UUID,
        *,
        for_update: bool = False,
        include_deleted: bool = False,
    ) -> MediaAsset | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_ids(
        self, media_asset_ids: list[uuid.UUID], *, include_deleted: bool = False
    ) -> list[MediaAsset]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_with_files(
        self,
        media_asset_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> MediaAsset | None:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        media_asset_id: uuid.UUID,
        status: MediaStatus,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def mark_deletion_pending(
        self,
        media_asset_id: uuid.UUID,
        *,
        deleted_at: datetime,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def mark_deleted(self, media_asset_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_stale_pending(
        self,
        *,
        created_before: datetime,
        limit: int = 100,
    ) -> list[MediaAsset]:
        raise NotImplementedError

    @abstractmethod
    async def list_deletion_pending(
        self,
        *,
        deleted_before: datetime,
        limit: int = 100,
    ) -> list[MediaAsset]:
        raise NotImplementedError
