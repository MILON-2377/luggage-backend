import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product import Product
    from app.modules.catalog.models.product_attribute import ProductAttribute


class ProductAttributeValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_attribute_values"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
            name="fk_product_attribute_values_product_id",
        ),
        nullable=False,
    )

    attribute_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_attributes.id",
            ondelete="RESTRICT",
            name="fk_product_attribute_values_attribute_id",
        ),
        nullable=True,
    )

    custom_attribute_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    custom_attribute_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_custom: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="attribute_values",
        lazy="raise",
    )

    attribute: Mapped["ProductAttribute | None"] = relationship(
        "ProductAttribute",
        back_populates="product_values",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_attribute_values_product_attribute",
            "product_id",
            "attribute_id",
            unique=True,
            postgresql_where=text("attribute_id IS NOT NULL"),
        ),
        Index(
            "uq_product_attribute_values_product_custom_name",
            "product_id",
            text("lower(custom_attribute_name)"),
            unique=True,
            postgresql_where=text("is_custom"),
        ),
        Index(
            "ix_product_attribute_values_product_order",
            "product_id",
            "display_order",
        ),
        Index(
            "ix_product_attribute_values_attribute_value",
            "attribute_id",
            text("left(value, 255)"),
            postgresql_where=text("attribute_id IS NOT NULL"),
        ),
        CheckConstraint(
            "(is_custom AND attribute_id IS NULL "
            "AND custom_attribute_name IS NOT NULL) "
            "OR (NOT is_custom AND attribute_id IS NOT NULL "
            "AND custom_attribute_name IS NULL "
            "AND custom_attribute_unit IS NULL)",
            name="ck_product_attribute_values_custom_consistency",
        ),
        CheckConstraint(
            "custom_attribute_name IS NULL OR length(trim(custom_attribute_name)) > 0",
            name="ck_product_attribute_values_custom_name_not_blank",
        ),
        CheckConstraint(
            "custom_attribute_unit IS NULL OR length(trim(custom_attribute_unit)) > 0",
            name="ck_product_attribute_values_custom_unit_not_blank",
        ),
        CheckConstraint(
            "length(trim(value)) > 0",
            name="ck_product_attribute_values_value_not_blank",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_product_attribute_values_display_order_non_negative",
        ),
    )

    @validates("value")
    def _strip_value(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("custom_attribute_name", "custom_attribute_unit")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
