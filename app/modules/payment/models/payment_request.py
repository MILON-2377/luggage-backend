import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
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
from app.modules.payment.enums import (
    PaymentGateway,
    PaymentMethod,
    PaymentRequestStatus,
    PaymentType,
)

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser
    from app.modules.payment.models.payment_event import PaymentEvent
    from app.modules.quotation.models.quotation import Quotation
    from app.modules.quotation.models.quotation_version import QuotationVersion


class PaymentRequest(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "payment_requests"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotations.id",
            ondelete="RESTRICT",
            name="fk_payment_requests_quotation_id",
        ),
        nullable=False,
    )

    quotation_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotation_versions.id",
            ondelete="RESTRICT",
            name="fk_payment_requests_quotation_version_id",
        ),
        nullable=False,
    )

    payment_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(
            PaymentType,
            name="payment_type",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    installment_number: Mapped[int | None] = mapped_column(
        Integer,
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

    status: Mapped[PaymentRequestStatus] = mapped_column(
        Enum(
            PaymentRequestStatus,
            name="payment_request_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=PaymentRequestStatus.PENDING,
        server_default=PaymentRequestStatus.PENDING.value,
        nullable=False,
    )

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(
            PaymentMethod,
            name="payment_method",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=50,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
    )

    payment_gateway: Mapped[PaymentGateway | None] = mapped_column(
        Enum(
            PaymentGateway,
            name="payment_gateway",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=50,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
    )

    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_payment_requests_created_by",
        ),
        nullable=True,
    )

    quotation: Mapped["Quotation"] = relationship(
        "Quotation",
        foreign_keys=[quotation_id],
        lazy="raise",
    )

    quotation_version: Mapped["QuotationVersion"] = relationship(
        "QuotationVersion",
        foreign_keys=[quotation_version_id],
        lazy="raise",
    )

    creator: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[created_by],
        lazy="raise",
    )

    events: Mapped[list["PaymentEvent"]] = relationship(
        "PaymentEvent",
        back_populates="payment_request",
        foreign_keys="PaymentEvent.payment_request_id",
        passive_deletes="all",
        lazy="raise",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["quotation_id", "quotation_version_id"],
            ["quotation_versions.quotation_id", "quotation_versions.id"],
            ondelete="RESTRICT",
            name="fk_payment_requests_version_belongs_to_quotation",
        ),
        Index(
            "uq_payment_requests_payment_number",
            "payment_number",
            unique=True,
        ),
        Index(
            "uq_payment_requests_gateway_payment",
            "payment_gateway",
            "gateway_payment_id",
            unique=True,
            postgresql_where=text("gateway_payment_id IS NOT NULL"),
        ),
        Index(
            "uq_payment_requests_quotation_installment_active",
            "quotation_id",
            "installment_number",
            unique=True,
            postgresql_where=text(
                "installment_number IS NOT NULL "
                "AND deleted_at IS NULL "
                "AND status NOT IN ('cancelled', 'expired')"
            ),
        ),
        Index(
            "ix_payment_requests_quotation_created_at_active",
            "quotation_id",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_payment_requests_quotation_version_id",
            "quotation_version_id",
        ),
        Index(
            "ix_payment_requests_active_status_created_at",
            "status",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_payment_requests_pending_due_at",
            "due_at",
            postgresql_where=text(
                "status IN ('pending', 'processing') "
                "AND due_at IS NOT NULL "
                "AND deleted_at IS NULL"
            ),
        ),
        Index(
            "ix_payment_requests_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(payment_number)) > 0",
            name="ck_payment_requests_payment_number_not_blank",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payment_requests_amount_positive",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_payment_requests_currency_format",
        ),
        CheckConstraint(
            "installment_number IS NULL OR installment_number > 0",
            name="ck_payment_requests_installment_number_positive",
        ),
        CheckConstraint(
            "(payment_type = 'installment') = (installment_number IS NOT NULL)",
            name="ck_payment_requests_installment_number_matches_type",
        ),
        CheckConstraint(
            "(status IN ('paid', 'refunded')) = (paid_at IS NOT NULL)",
            name="ck_payment_requests_paid_at_matches_status",
        ),
        CheckConstraint(
            "payment_gateway IS NULL "
            "OR payment_gateway = 'manual' "
            "OR status = 'pending' "
            "OR gateway_payment_id IS NOT NULL",
            name="ck_payment_requests_gateway_requires_payment_id",
        ),
    )

    @validates("payment_number")
    def _strip_payment_number(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates("gateway_payment_id", "description")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
