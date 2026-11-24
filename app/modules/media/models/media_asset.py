import uuid

from sqlalchemy import (
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
from app.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.authentication.models.admin_user_profile import AdminUserProfile
from app.modules.media.enums import MediaStatus, MediaType
from app.modules.media.models.media_file import MediaFile


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "media_assets"

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    media_type: Mapped[MediaType] = mapped_column(
        Enum(
            MediaType,
            name="media_type",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    status: Mapped[MediaStatus] = mapped_column(
        Enum(
            MediaStatus,
            name="media_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=MediaStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_media_assets_uploaded_by",
        ),
        nullable=True,
    )

    uploader: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[uploaded_by],
        lazy="raise",
    )

    avatar_profiles: Mapped[list["AdminUserProfile"]] = relationship(
        "AdminUserProfile",
        back_populates="avatar_media",
        foreign_keys="AdminUserProfile.avatar_media_id",
        passive_deletes=True,
        lazy="raise",
    )

    # DB-level ON DELETE CASCADE does the work; passive_deletes stops the ORM
    # from loading every file just to delete it.
    files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile",
        back_populates="media_asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_media_assets_uploaded_by",
            "uploaded_by",
        ),
        Index(
            "ix_media_assets_active_type_created_at",
            "media_type",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_media_assets_active_status",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_media_assets_original_filename_not_blank",
        ),
        # Status and deleted_at are two signals for deletion; a deletion
        # status without a timestamp would be inconsistent.
        CheckConstraint(
            "status NOT IN ('deletion_pending', 'deleted') OR deleted_at IS NOT NULL",
            name="ck_media_assets_deletion_status_requires_deleted_at",
        ),
    )

    @validates("original_filename")
    def _strip_original_filename(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("display_name", "title", "alt_text", "description")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
