import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin
from app.modules.media.enums import MediaFileRole

if TYPE_CHECKING:
    from app.modules.media.models.media_asset import MediaAsset
    from app.modules.media.models.media_storage_location import MediaStorageLocation


class MediaFile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "media_files"

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_assets.id",
            ondelete="CASCADE",
            name="fk_media_files_media_asset_id",
        ),
        nullable=False,
    )

    file_role: Mapped[MediaFileRole] = mapped_column(
        Enum(
            MediaFileRole,
            name="media_file_role",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    file_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    duration: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    media_asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        back_populates="files",
        lazy="raise",
    )

    storage_locations: Mapped[list["MediaStorageLocation"]] = relationship(
        "MediaStorageLocation",
        back_populates="media_file",
        passive_deletes="all",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_media_files_asset_id_file_role",
            "media_asset_id",
            "file_role",
            unique=True,
        ),
        Index(
            "ix_media_files_checksum",
            "checksum",
            postgresql_where=text("checksum IS NOT NULL"),
        ),
        CheckConstraint(
            "file_size > 0",
            name="ck_media_files_file_size_positive",
        ),
        CheckConstraint(
            "width IS NULL OR width > 0",
            name="ck_media_files_width_positive",
        ),
        CheckConstraint(
            "height IS NULL OR height > 0",
            name="ck_media_files_height_positive",
        ),
        CheckConstraint(
            "duration IS NULL OR duration >= 0",
            name="ck_media_files_duration_non_negative",
        ),
        CheckConstraint(
            "(width IS NULL) = (height IS NULL)",
            name="ck_media_files_dimensions_together",
        ),
        CheckConstraint(
            "checksum IS NULL OR "
            "(length(checksum) IN (64, 128) AND checksum ~ '^[0-9a-f]+$')",
            name="ck_media_files_checksum_format",
        ),
        CheckConstraint(
            "file_format = lower(file_format) AND file_format ~ '^[a-z0-9]+$'",
            name="ck_media_files_file_format_format",
        ),
        CheckConstraint(
            "mime_type = lower(mime_type) "
            "AND mime_type ~ '^[a-z0-9.+-]+/[a-z0-9.+-]+$'",
            name="ck_media_files_mime_type_format",
        ),
    )

    @validates("file_format", "mime_type", "checksum")
    def _normalize_lower(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()
