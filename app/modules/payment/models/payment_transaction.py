import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.payment.enums import PaymentMethod, PaymentTransactionStatus

if TYPE_CHECKING:
    from app.modules.payment.models.payment_event import PaymentEvent
    from app.modules.payment.models.payment_request import PaymentRequest


class PaymentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_transactions"

    payment_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "payment_requests.id",
            ondelete="RESTRICT",
            name="fk_payment_transactions_payment_request_id",
        ),
        nullable=False,
    )

    transaction_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(
            PaymentMethod,
            name="payment_transaction_method",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=50,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    status: Mapped[PaymentTransactionStatus] = mapped_column(
        Enum(
            PaymentTransactionStatus,
            name="payment_transaction_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=PaymentTransactionStatus.PENDING,
        server_default=PaymentTransactionStatus.PENDING.value,
        nullable=False,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    gateway_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payment_request: Mapped["PaymentRequest"] = relationship(
        "PaymentRequest",
        back_populates="transactions",
        lazy="raise",
    )

    events: Mapped[list["PaymentEvent"]] = relationship(
        "PaymentEvent",
        back_populates="payment_transaction",
        foreign_keys="PaymentEvent.payment_transaction_id",
        passive_deletes="all",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_payment_transactions_transaction_number",
            "transaction_number",
            unique=True,
        ),
        Index(
            "uq_payment_transactions_gateway_transaction_id",
            "gateway_transaction_id",
            unique=True,
            postgresql_where=text("gateway_transaction_id IS NOT NULL"),
        ),
        Index(
            "ix_payment_transactions_request_created_at",
            "payment_request_id",
            text("created_at DESC"),
        ),
        Index(
            "uq_payment_transactions_one_succeeded_per_request",
            "payment_request_id",
            unique=True,
            postgresql_where=text("status = 'succeeded'"),
        ),
        Index(
            "ix_payment_transactions_in_flight_created_at",
            "created_at",
            postgresql_where=text("status IN ('pending', 'processing')"),
        ),
        CheckConstraint(
            "length(trim(transaction_number)) > 0",
            name="ck_payment_transactions_transaction_number_not_blank",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payment_transactions_amount_positive",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_payment_transactions_currency_format",
        ),
        CheckConstraint(
            "(status IN ('pending', 'processing')) = (processed_at IS NULL)",
            name="ck_payment_transactions_processed_at_matches_status",
        ),
        CheckConstraint(
            "failure_code IS NULL OR status = 'failed'",
            name="ck_payment_transactions_failure_only_when_failed",
        ),
        CheckConstraint(
            "failure_message IS NULL OR status = 'failed'",
            name="ck_payment_transactions_failure_message_only_when_failed",
        ),
        CheckConstraint(
            "gateway_response IS NULL OR jsonb_typeof(gateway_response) = 'object'",
            name="ck_payment_transactions_gateway_response_is_object",
        ),
    )

    @validates("transaction_number")
    def _strip_transaction_number(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates(
        "gateway_transaction_id",
        "failure_code",
        "failure_message",
    )
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
