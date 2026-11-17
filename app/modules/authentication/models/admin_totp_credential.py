import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class AdminTotpCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_totp_credentials"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_admin_totp_credentials_admin_user_id",
        ),
        nullable=False,
    )

    secret_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    algorithm: Mapped[str] = mapped_column(
        String(10),
        default="SHA1",
        server_default=text("'SHA1'"),
        nullable=False,
    )

    digits: Mapped[int] = mapped_column(
        Integer,
        default=6,
        server_default=text("6"),
        nullable=False,
    )

    period_seconds: Mapped[int] = mapped_column(
        Integer,
        default=30,
        server_default=text("30"),
        nullable=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_used_time_step: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_admin_totp_credentials_active_by_user",
            "admin_user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        CheckConstraint(
            "algorithm IN ('SHA1', 'SHA256', 'SHA512')",
            name="ck_admin_totp_credentials_algorithm_valid",
        ),
        CheckConstraint(
            "digits IN (6, 8)",
            name="ck_admin_totp_credentials_digits_valid",
        ),
        CheckConstraint(
            "period_seconds > 0",
            name="ck_admin_totp_credentials_period_positive",
        ),
        CheckConstraint(
            "last_used_time_step IS NULL OR last_used_time_step >= 0",
            name="ck_admin_totp_credentials_time_step_non_negative",
        ),
        CheckConstraint(
            "last_used_at IS NULL OR verified_at IS NOT NULL",
            name="ck_admin_totp_credentials_used_requires_verified",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR verified_at IS NOT NULL",
            name="ck_admin_totp_credentials_revoked_requires_verified",
        ),
    )
