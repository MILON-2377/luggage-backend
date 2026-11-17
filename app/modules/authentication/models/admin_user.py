from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.authentication.enums import AdminUserStatus

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user_profile import AdminUserProfile


class AdminUser(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[AdminUserStatus] = mapped_column(
        Enum(
            AdminUserStatus,
            name="admin_user_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=AdminUserStatus.INVITED,
        server_default=AdminUserStatus.INVITED.value,
        nullable=False,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    profile: Mapped["AdminUserProfile | None"] = relationship(
        "AdminUserProfile",
        back_populates="admin_user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_admin_users_email_lower_active",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_admin_users_failed_login_attempts_non_negative",
        ),
        CheckConstraint(
            "status = 'invited' OR password_hash IS NOT NULL",
            name="ck_admin_users_password_required_when_not_invited",
        ),
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()
