
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.authentication.enums import ChallengeType

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class AuthChallenge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_challenges"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_auth_challenges_admin_user_id",
        ),
        nullable=False,
    )

    challenge_type: Mapped[ChallengeType] = mapped_column(
        Enum(
            ChallengeType,
            name="challenge_type",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    # Store an HMAC-SHA256 hex digest, never the raw token or OTP.
    challenge_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Store non-sensitive challenge metadata only.
    challenge_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=5,
        server_default=text("5"),
        nullable=False,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_auth_challenges_challenge_token_hash",
            "challenge_token_hash",
            unique=True,
        ),
        Index(
            "ix_auth_challenges_pending_by_user_type",
            "admin_user_id",
            "challenge_type",
            postgresql_where=text("consumed_at IS NULL"),
        ),
        Index(
            "ix_auth_challenges_expires_at",
            "expires_at",
        ),
        CheckConstraint(
            "failed_attempts >= 0",
            name="ck_auth_challenges_failed_attempts_non_negative",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_auth_challenges_max_attempts_positive",
        ),
        CheckConstraint(
            "failed_attempts <= max_attempts",
            name="ck_auth_challenges_failed_attempts_within_max",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_challenges_expires_after_created",
        ),
    )
