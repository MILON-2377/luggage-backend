import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
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
from app.core.enums.record_status import RecordStatus

if TYPE_CHECKING:
    from app.modules.catalog.models.product import Product


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
            name="fk_product_variants_product_id",
        ),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    variant_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    variant_value: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    additional_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default=text("0"),
        nullable=False,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    status: Mapped[RecordStatus] = mapped_column(
        Enum(
            RecordStatus,
            name="record_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=20,
            create_constraint=True,
            validate_strings=True,
        ),
        default=RecordStatus.DRAFT,
        server_default=RecordStatus.DRAFT.value,
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="variants",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_variants_sku_lower_active",
            text("lower(sku)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_product_variants_product_type_value_active",
            "product_id",
            text("lower(variant_type)"),
            text("lower(variant_value)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_product_variants_product_order_active",
            "product_id",
            "display_order",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "length(trim(sku)) > 0",
            name="ck_product_variants_sku_not_blank",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_product_variants_name_not_blank",
        ),
        CheckConstraint(
            "variant_type ~ '^[a-z0-9]+(_[a-z0-9]+)*$'",
            name="ck_product_variants_variant_type_format",
        ),
        CheckConstraint(
            "length(trim(variant_value)) > 0",
            name="ck_product_variants_variant_value_not_blank",
        ),
        CheckConstraint(
            "additional_price >= 0",
            name="ck_product_variants_additional_price_non_negative",
        ),
        CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'",
            name="ck_product_variants_currency_format",
        ),
        CheckConstraint(
            "additional_price = 0 OR currency IS NOT NULL",
            name="ck_product_variants_price_requires_currency",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_product_variants_display_order_non_negative",
        ),
    )

    @validates("sku", "name", "variant_value")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("variant_type")
    def _normalize_variant_type(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper() or None
