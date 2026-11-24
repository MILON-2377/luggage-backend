import uuid
from abc import ABC, abstractmethod

from app.modules.media.dtos.upload import (
    ConfirmUploadResultDTO,
    CreateUploadDTO,
    CreateUploadResultDTO,
)


class AbstractMediaService(ABC):
    @abstractmethod
    async def create_upload(
        self,
        payload: CreateUploadDTO,
    ) -> CreateUploadResultDTO:
        raise NotImplementedError

    @abstractmethod
    async def confirm_upload(
        self,
        media_asset_id: uuid.UUID,
    ) -> ConfirmUploadResultDTO:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, media_asset_id: uuid.UUID) -> None:
        raise NotImplementedError
