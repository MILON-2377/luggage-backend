import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin
from app.modules.authentication.models.admin_user import AdminUser

if TYPE_CHECKING:
    from app.modules.quotation.models.quotation import Quotation
    from app.modules.quotation.models.quotation_item import QuotationItem


class QuotationVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quotation_versions"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotations.id",
            ondelete="CASCADE",
            name="fk_quotation_versions_quotation_id",
        ),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_quotation_versions_created_by",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quotation: Mapped["Quotation"] = relationship(
        "Quotation",
        foreign_keys=[quotation_id],
        back_populates="versions",
        lazy="raise",
    )

    creator: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[created_by],
        lazy="raise",
    )

    items: Mapped[list["QuotationItem"]] = relationship(
        "QuotationItem",
        back_populates="quotation_version",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_quotation_versions_quotation_version_number",
            "quotation_id",
            "version_number",
            unique=True,
        ),
        Index(
            "uq_quotation_versions_quotation_id_id",
            "quotation_id",
            "id",
            unique=True,
        ),
        Index(
            "ix_quotation_versions_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        CheckConstraint(
            "version_number > 0",
            name="ck_quotation_versions_version_number_positive",
        ),
        CheckConstraint(
            "subtotal >= 0 AND discount_amount >= 0 "
            "AND shipping_cost >= 0 AND tax_amount >= 0 "
            "AND total_amount >= 0",
            name="ck_quotation_versions_amounts_non_negative",
        ),
        CheckConstraint(
            "discount_amount <= subtotal",
            name="ck_quotation_versions_discount_within_subtotal",
        ),
        CheckConstraint(
            "total_amount = subtotal - discount_amount + shipping_cost + tax_amount",
            name="ck_quotation_versions_total_matches_components",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_quotation_versions_currency_format",
        ),
    )

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str) -> str:
        return value.strip().upper()

    @validates("payment_terms", "delivery_terms", "notes")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
