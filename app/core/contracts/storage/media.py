from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.modules.media.enums import MediaType, StorageProvider


@dataclass(frozen=True, slots=True)
class SignedUpload:
    upload_url: str
    upload_params: dict[str, str]


@dataclass(frozen=True, slots=True)
class VerifiedAsset:
    public_id: str
    resource_type: str
    mime_type: str
    file_format: str | None = None
    file_size: int | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    secure_url: str | None = None


class AbstractMediaStorage(ABC):
    @property
    @abstractmethod
    def provider(self) -> StorageProvider:
        raise NotImplementedError

    @abstractmethod
    async def create_signed_upload(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        mime_type: str,
        expires_in: int,
    ) -> SignedUpload:
        raise NotImplementedError

    @abstractmethod
    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def delete_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def verify_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        expected_mime_type: str,
        expected_file_format: str | None = None,
    ) -> VerifiedAsset:
        raise NotImplementedError
