import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser
    from app.modules.media.models.media_asset import MediaAsset


class AdminUserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_user_profiles"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_admin_user_profiles_admin_user_id",
        ),
        nullable=False,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    avatar_media_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_assets.id",
            ondelete="SET NULL",
            name="fk_admin_user_profiles_avatar_media_id",
        ),
        nullable=True,
    )

    job_title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        default="Asia/Shanghai",
        server_default=text("'Asia/Shanghai'"),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        server_default=text("'en'"),
        nullable=False,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    avatar_media: Mapped["MediaAsset | None"] = relationship(
        "MediaAsset",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_admin_user_profiles_admin_user_id",
            "admin_user_id",
            unique=True,
        ),
        Index(
            "ix_admin_user_profiles_avatar_media_id",
            "avatar_media_id",
            postgresql_where=text("avatar_media_id IS NOT NULL"),
        ),
        CheckConstraint(
            "first_name IS NULL OR length(trim(first_name)) > 0",
            name="ck_admin_user_profiles_first_name_not_blank",
        ),
        CheckConstraint(
            "last_name IS NULL OR length(trim(last_name)) > 0",
            name="ck_admin_user_profiles_last_name_not_blank",
        ),
        CheckConstraint(
            "display_name IS NULL OR length(trim(display_name)) > 0",
            name="ck_admin_user_profiles_display_name_not_blank",
        ),
        CheckConstraint(
            "phone IS NULL OR phone ~ '^\\+[1-9][0-9]{6,14}$'",
            name="ck_admin_user_profiles_phone_e164",
        ),
        CheckConstraint(
            "language ~ '^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$'",
            name="ck_admin_user_profiles_language_format",
        ),
        CheckConstraint(
            "length(trim(timezone)) > 0",
            name="ck_admin_user_profiles_timezone_not_blank",
        ),
    )

    @validates(
        "first_name",
        "last_name",
        "display_name",
        "phone",
        "job_title",
        "department",
        "timezone",
        "language",
    )
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None