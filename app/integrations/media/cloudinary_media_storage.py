import asyncio
import time
from typing import Any

import cloudinary.api
import cloudinary.utils
from cloudinary.exceptions import NotFound

from app.core.contracts.storage.errors import (
    AssetMimeTypeMismatchError,
    AssetNotFoundError,
    AssetPublicIdMismatchError,
    AssetResourceTypeMismatchError,
)
from app.core.contracts.storage.media import (
    AbstractMediaStorage,
    SignedUpload,
    VerifiedAsset,
)
from app.modules.media.enums import MediaType, StorageProvider
from app.modules.media.errors.media import UnsupportedMediaTypeError

_FORMAT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
    "avif": "image/avif",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mov": "video/quicktime",
    "pdf": "application/pdf",
}

_CLOUDINARY_RESOURCE_TYPES = {
    MediaType.IMAGE: "image",
    MediaType.VIDEO: "video",
    MediaType.DOCUMENT: "raw",
}


class CloudinaryMediaStorage(AbstractMediaStorage):
    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        upload_preset: str,
    ) -> None:
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._upload_preset = upload_preset

    @property
    def provider(self) -> StorageProvider:
        return StorageProvider.CLOUDINARY

    @property
    def _credentials(self) -> dict[str, Any]:
        return {
            "cloud_name": self._cloud_name,
            "api_key": self._api_key,
            "api_secret": self._api_secret,
            "secure": True,
        }

    @staticmethod
    def _get_resource_type(media_type: MediaType) -> str:
        try:
            return _CLOUDINARY_RESOURCE_TYPES[media_type]
        except KeyError as exc:
            raise UnsupportedMediaTypeError(media_type) from exc

    async def create_signed_upload(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        mime_type: str,
        expires_in: int,
    ) -> SignedUpload:
        resource_type = self._get_resource_type(media_type)
        timestamp = int(time.time())

        signature = cloudinary.utils.api_sign_request(
            {
                "public_id": public_id,
                "timestamp": timestamp,
                "upload_preset": self._upload_preset,
            },
            self._api_secret,
        )

        return SignedUpload(
            upload_url=(
                f"https://api.cloudinary.com/v1_1/"
                f"{self._cloud_name}/{resource_type}/upload"
            ),
            upload_params={
                "public_id": public_id,
                "timestamp": str(timestamp),
                "upload_preset": self._upload_preset,
                "api_key": self._api_key,
                "signature": signature,
            },
        )

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> dict[str, Any]:
        resource_type = self._get_resource_type(media_type)

        try:
            return await asyncio.to_thread(
                cloudinary.api.resource,
                public_id,
                resource_type=resource_type,
                **self._credentials,
            )
        except NotFound as exc:
            raise AssetNotFoundError(public_id) from exc

    async def delete_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> None:
        resource_type = self._get_resource_type(media_type)

        await asyncio.to_thread(
            cloudinary.api.delete_resources,
            [public_id],
            resource_type=resource_type,
            **self._credentials,
        )

    async def verify_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        expected_mime_type: str,
        expected_file_format: str | None = None,
    ) -> VerifiedAsset:
        expected_resource_type = self._get_resource_type(media_type)

        metadata = await self.get_asset_metadata(
            public_id=public_id,
            media_type=media_type,
        )

        actual_public_id = metadata.get("public_id")
        actual_resource_type = metadata.get("resource_type")
        actual_format = metadata.get("format")

        if actual_public_id != public_id:
            raise AssetPublicIdMismatchError(
                expected=public_id,
                actual=actual_public_id,
            )

        if actual_resource_type != expected_resource_type:
            raise AssetResourceTypeMismatchError(
                expected=expected_resource_type,
                actual=actual_resource_type,
            )

        if actual_format is None and media_type == MediaType.DOCUMENT:
            # Raw resources carry no format; trust only the extension the
            # service recorded at create time, and only if it is a known one.
            actual_format = expected_file_format

        actual_mime_type = _FORMAT_TO_MIME.get(actual_format or "")

        if actual_mime_type != expected_mime_type:
            raise AssetMimeTypeMismatchError(
                expected=expected_mime_type,
                actual=actual_mime_type,
            )

        return VerifiedAsset(
            public_id=actual_public_id,
            resource_type=actual_resource_type,
            mime_type=actual_mime_type,
            file_format=actual_format,
            file_size=metadata.get("bytes"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            duration=metadata.get("duration"),
            secure_url=metadata.get("secure_url"),
        )
