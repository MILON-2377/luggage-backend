import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.media.enums import MediaStatus, MediaType

MIME_TYPE_PATTERN = r"^[a-z0-9.+-]+/[a-z0-9.+-]+$"


class CreateUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_filename: str = Field(min_length=1, max_length=255)
    media_type: MediaType
    mime_type: str = Field(min_length=3, max_length=100, pattern=MIME_TYPE_PATTERN)
    file_size: int = Field(gt=0)

    @field_validator("original_filename")
    @classmethod
    def _strip_filename(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("original_filename must not be blank.")
        return stripped

    @field_validator("mime_type", mode="before")
    @classmethod
    def _normalize_mime_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class CreateUploadResponse(BaseModel):
    media_asset_id: uuid.UUID
    upload_url: str
    upload_params: dict[str, str]


class ConfirmUploadResponse(BaseModel):
    media_asset_id: uuid.UUID
    status: MediaStatus
    media_type: MediaType
    mime_type: str
    file_format: str
    file_size: int
    width: int | None = None
    height: int | None = None
    duration: Decimal | None = None
    url: str | None = None