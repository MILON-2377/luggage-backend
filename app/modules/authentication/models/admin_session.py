import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin
from app.modules.authentication.enums import SessionRevocationReason
from app.modules.authentication.models.admin_user import AdminUser


class AdminSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "admin_sessions"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_admin_sessions_admin_user_id",
        ),
        nullable=False,
    )

    # Store a SHA-256 hex digest of the refresh token, never the raw token.
    refresh_token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    device_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    operating_system: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    ip_address: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revocation_reason: Mapped[SessionRevocationReason | None] = mapped_column(
        Enum(
            SessionRevocationReason,
            name="session_revocation_reason",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=100,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    __table_args__ = (
        # Token lookup on refresh; also guarantees hash uniqueness.
        Index(
            "uq_admin_sessions_refresh_token_hash",
            "refresh_token_hash",
            unique=True,
        ),
        # List/revoke a user's sessions; FK columns are not auto-indexed in Postgres.
        Index(
            "ix_admin_sessions_admin_user_id",
            "admin_user_id",
        ),
        # Fast lookup of a user's currently active sessions.
        Index(
            "ix_admin_sessions_active_by_user",
            "admin_user_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        # Cleanup job for expired sessions.
        Index(
            "ix_admin_sessions_expires_at",
            "expires_at",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_admin_sessions_expires_after_created",
        ),
        # A revocation reason only makes sense when the session is revoked.
        CheckConstraint(
            "(revoked_at IS NULL) = (revocation_reason IS NULL)",
            name="ck_admin_sessions_revocation_fields_consistent",
        ),
    )