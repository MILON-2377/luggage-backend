import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.media.enums import StorageLocationStatus, StorageProvider

if TYPE_CHECKING:
    from app.modules.media.models.media_file import MediaFile


class MediaStorageLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_storage_locations"

    media_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_files.id",
            ondelete="RESTRICT",
            name="fk_media_storage_locations_media_file_id",
        ),
        nullable=False,
    )

    storage_provider: Mapped[StorageProvider] = mapped_column(
        Enum(
            StorageProvider,
            name="storage_provider",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    storage_bucket: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    storage_region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    storage_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    status: Mapped[StorageLocationStatus] = mapped_column(
        Enum(
            StorageLocationStatus,
            name="storage_location_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=StorageLocationStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )

    media_file: Mapped["MediaFile"] = relationship(
        "MediaFile",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_media_storage_locations_media_file_id",
            "media_file_id",
        ),
        Index(
            "uq_media_storage_locations_primary_per_file",
            "media_file_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
        Index(
            "uq_media_storage_locations_object",
            "storage_provider",
            text("coalesce(storage_bucket, '')"),
            "storage_key",
            unique=True,
        ),
        Index(
            "ix_media_storage_locations_deletion_pending",
            "status",
            "updated_at",
            postgresql_where=text("status = 'deletion_pending'"),
        ),
        CheckConstraint(
            "length(trim(storage_key)) > 0",
            name="ck_media_storage_locations_storage_key_not_blank",
        ),
        CheckConstraint(
            "storage_key NOT LIKE '/%'",
            name="ck_media_storage_locations_storage_key_no_leading_slash",
        ),
        CheckConstraint(
            "NOT is_primary OR status = 'ready'",
            name="ck_media_storage_locations_primary_must_be_ready",
        ),
    )

    @validates("storage_bucket", "storage_region", "storage_url")
    def _strip_optional(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @validates("storage_key")
    def _strip_key(self, _key: str, value: str) -> str:
        return value.strip()