import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product import Product
    from app.modules.catalog.models.product_variant import ProductVariant
    from app.modules.inquiry.models.inquiry import Inquiry


class InquiryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inquiry_items"

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "inquiries.id",
            ondelete="CASCADE",
            name="fk_inquiry_items_inquiry_id",
        ),
        nullable=False,
    )

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
            name="fk_inquiry_items_product_id",
        ),
        nullable=True,
    )

    product_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_variants.id",
            ondelete="SET NULL",
            name="fk_inquiry_items_product_variant_id",
        ),
        nullable=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    product_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )

    target_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    specifications: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    inquiry: Mapped["Inquiry"] = relationship(
        "Inquiry",
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
            "ix_inquiry_items_inquiry_id",
            "inquiry_id",
        ),
        Index(
            "ix_inquiry_items_product_id",
            "product_id",
            postgresql_where=text("product_id IS NOT NULL"),
        ),
        Index(
            "ix_inquiry_items_product_variant_id",
            "product_variant_id",
            postgresql_where=text("product_variant_id IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(product_name)) > 0",
            name="ck_inquiry_items_product_name_not_blank",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_inquiry_items_quantity_positive",
        ),
        CheckConstraint(
            "target_price IS NULL OR target_price >= 0",
            name="ck_inquiry_items_target_price_non_negative",
        ),
        CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'",
            name="ck_inquiry_items_currency_format",
        ),
        CheckConstraint(
            "target_price IS NULL OR currency IS NOT NULL",
            name="ck_inquiry_items_target_price_requires_currency",
        ),
        CheckConstraint(
            "product_variant_id IS NULL OR product_id IS NOT NULL",
            name="ck_inquiry_items_variant_requires_product",
        ),
        CheckConstraint(
            "specifications IS NULL OR jsonb_typeof(specifications) = 'object'",
            name="ck_inquiry_items_specifications_is_object",
        ),
    )

    @validates("product_name")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("product_code")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper() or None
