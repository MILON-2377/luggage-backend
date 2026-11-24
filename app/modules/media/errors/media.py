import uuid

from app.core.errors.base import ConflictError, NotFoundError, ValidationError
from app.modules.media.enums import MediaStatus, MediaType


class MediaAssetNotFoundError(NotFoundError):
    error_code = "MEDIA_ASSET_NOT_FOUND"
    default_message = "The media asset was not found."

    def __init__(self, media_asset_id: uuid.UUID) -> None:
        self.media_asset_id = media_asset_id
        super().__init__(details={"media_asset_id": str(media_asset_id)})


class MediaFileNotFoundError(NotFoundError):
    error_code = "MEDIA_FILE_NOT_FOUND"
    default_message = "The media file was not found."

    def __init__(self, media_asset_id: uuid.UUID) -> None:
        self.media_asset_id = media_asset_id
        super().__init__(details={"media_asset_id": str(media_asset_id)})


class MediaStorageLocationNotFoundError(NotFoundError):
    error_code = "MEDIA_STORAGE_LOCATION_NOT_FOUND"
    default_message = "The media storage location was not found."

    def __init__(self, media_asset_id: uuid.UUID) -> None:
        self.media_asset_id = media_asset_id
        super().__init__(details={"media_asset_id": str(media_asset_id)})


class MediaNotPendingError(ConflictError):
    error_code = "MEDIA_NOT_PENDING"
    default_message = "The media asset is not awaiting upload confirmation."

    def __init__(self, *, media_asset_id: uuid.UUID, status: MediaStatus) -> None:
        self.media_asset_id = media_asset_id
        self.status = status
        super().__init__(
            details={
                "media_asset_id": str(media_asset_id),
                "status": status.value,
            }
        )


class UnsupportedMediaTypeError(ValidationError):
    error_code = "UNSUPPORTED_MEDIA_TYPE"
    default_message = "The media type is not supported by the storage provider."

    def __init__(self, media_type: MediaType) -> None:
        self.media_type = media_type
        super().__init__(details={"media_type": media_type.value})
