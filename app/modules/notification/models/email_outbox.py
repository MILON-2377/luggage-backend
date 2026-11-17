from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.notification.enums import EmailOutboxStatus

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class EmailOutbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "email_outbox"

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payload_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[EmailOutboxStatus] = mapped_column(
        Enum(
            EmailOutboxStatus,
            name="email_outbox_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=EmailOutboxStatus.PENDING,
        server_default=text("'pending'"),
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    max_attempts: Mapped[int] = mapped_column(
        default=3,
        server_default=text("3"),
        nullable=False,
    )

    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "uq_email_outbox_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index(
            "ix_email_outbox_pending_dispatch",
            "next_attempt_at",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_email_outbox_processing_locked_at",
            "locked_at",
            postgresql_where=text("status = 'processing'"),
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_email_outbox_attempt_count_non_negative",
        ),
        CheckConstraint(
            "payload_encrypted IS NULL OR length(payload_encrypted) > 0",
            name="ck_email_outbox_payload_not_empty",
        ),
        CheckConstraint(
            "max_attempts > 0",
            name="ck_email_outbox_max_attempts_positive",
        ),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_email_outbox_attempt_count_within_limit",
        ),
        CheckConstraint(
            "(status = 'processing') = (locked_at IS NOT NULL)",
            name="ck_email_outbox_locked_at_matches_status",
        ),
        CheckConstraint(
            "(status = 'sent') = (sent_at IS NOT NULL)",
            name="ck_email_outbox_sent_at_matches_status",
        ),
        CheckConstraint(
            "(status = 'failed') = (failed_at IS NOT NULL)",
            name="ck_email_outbox_failed_at_matches_status",
        ),
        CheckConstraint(
            "length(trim(provider)) > 0",
            name="ck_email_outbox_provider_not_blank",
        ),
    )
