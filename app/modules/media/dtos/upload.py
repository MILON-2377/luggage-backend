import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.modules.media.enums import MediaStatus, MediaType


@dataclass(frozen=True, slots=True)
class CreateUploadDTO:
    original_filename: str
    media_type: MediaType
    mime_type: str
    file_size: int
    uploaded_by: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateUploadResultDTO:
    media_asset_id: uuid.UUID
    upload_url: str
    upload_params: dict[str, str]


@dataclass(frozen=True, slots=True)
class ConfirmUploadResultDTO:
    media_asset_id: uuid.UUID
    status: MediaStatus
    media_type: MediaType
    mime_type: str
    file_format: str
    file_size: int
    width: int | None
    height: int | None
    duration: Decimal | None
    url: str | None