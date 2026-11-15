import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.payment.models.payment_request import PaymentRequest
    from app.modules.payment.models.payment_transaction import PaymentTransaction


class PaymentEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_events"

    payment_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "payment_requests.id",
            ondelete="RESTRICT",
            name="fk_payment_events_payment_request_id",
        ),
        nullable=True,
    )

    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "payment_transactions.id",
            ondelete="RESTRICT",
            name="fk_payment_events_payment_transaction_id",
        ),
        nullable=True,
    )

    gateway_event_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    signature_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payment_request: Mapped["PaymentRequest | None"] = relationship(
        "PaymentRequest",
        back_populates="events",
        foreign_keys=[payment_request_id],
        lazy="raise",
    )

    payment_transaction: Mapped["PaymentTransaction | None"] = relationship(
        "PaymentTransaction",
        back_populates="events",
        foreign_keys=[payment_transaction_id],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_payment_events_gateway_event_id",
            "gateway_event_id",
            unique=True,
            postgresql_where=text("gateway_event_id IS NOT NULL"),
        ),
        Index(
            "ix_payment_events_request_created_at",
            "payment_request_id",
            "created_at",
            postgresql_where=text("payment_request_id IS NOT NULL"),
        ),
        Index(
            "ix_payment_events_transaction_id",
            "payment_transaction_id",
            postgresql_where=text("payment_transaction_id IS NOT NULL"),
        ),
        Index(
            "ix_payment_events_unprocessed_created_at",
            "created_at",
            postgresql_where=text("processed_at IS NULL AND signature_verified"),
        ),
        CheckConstraint(
            "length(trim(event_type)) > 0",
            name="ck_payment_events_event_type_not_blank",
        ),
        CheckConstraint(
            "jsonb_typeof(event_data) = 'object'",
            name="ck_payment_events_event_data_is_object",
        ),
        CheckConstraint(
            "processed_at IS NULL OR signature_verified",
            name="ck_payment_events_processed_requires_verified",
        ),
    )

    @validates("event_type")
    def _strip_event_type(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("gateway_event_id")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
