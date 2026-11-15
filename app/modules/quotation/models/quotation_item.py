import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product import Product
    from app.modules.catalog.models.product_variant import ProductVariant
    from app.modules.quotation.models.quotation_version import QuotationVersion


class QuotationItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quotation_items"

    quotation_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotation_versions.id",
            ondelete="CASCADE",
            name="fk_quotation_items_quotation_version_id",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
            name="fk_quotation_items_product_id",
        ),
        nullable=True,
    )

    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_variants.id",
            ondelete="SET NULL",
            name="fk_quotation_items_product_variant_id",
        ),
        nullable=True,
    )

    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    specifications: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quotation_version: Mapped["QuotationVersion"] = relationship(
        "QuotationVersion",
        back_populates="items",
        lazy="raise",
    )

    product: Mapped["Product | None"] = relationship(
        "Product",
        lazy="raise",
    )

    product_variant: Mapped["ProductVariant | None"] = relationship(
        "ProductVariant",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_quotation_items_version_created_at",
            "quotation_version_id",
            "created_at",
        ),
        Index(
            "ix_quotation_items_product_id",
            "product_id",
            postgresql_where=text("product_id IS NOT NULL"),
        ),
        Index(
            "ix_quotation_items_product_variant_id",
            "product_variant_id",
            postgresql_where=text("product_variant_id IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(product_name)) > 0",
            name="ck_quotation_items_product_name_not_blank",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_quotation_items_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0 AND discount_amount >= 0 AND total_price >= 0",
            name="ck_quotation_items_amounts_non_negative",
        ),
        CheckConstraint(
            "discount_amount <= quantity * unit_price",
            name="ck_quotation_items_discount_within_line",
        ),
        CheckConstraint(
            "total_price = quantity * unit_price - discount_amount",
            name="ck_quotation_items_total_matches_components",
        ),
        CheckConstraint(
            "product_variant_id IS NULL OR product_id IS NOT NULL",
            name="ck_quotation_items_variant_requires_product",
        ),
        CheckConstraint(
            "specifications IS NULL OR jsonb_typeof(specifications) = 'object'",
            name="ck_quotation_items_specifications_is_object",
        ),
    )

    @validates("product_name")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("product_code", "description")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
