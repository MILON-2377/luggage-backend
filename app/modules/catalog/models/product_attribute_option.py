import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product_attribute import ProductAttribute
    from app.modules.catalog.models.product_attribute_value_option import (
        ProductAttributeValueOption,
    )


class ProductAttributeOption(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_attribute_options"

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_attributes.id",
            ondelete="CASCADE",
            name="fk_product_attribute_options_attribute_id",
        ),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    attribute: Mapped["ProductAttribute"] = relationship(
        "ProductAttribute",
        back_populates="options",
        lazy="raise",
    )

    product_value_options: Mapped[list["ProductAttributeValueOption"]] = relationship(
        "ProductAttributeValueOption",
        back_populates="option",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_attribute_options_attribute_value",
            "attribute_id",
            text("lower(value)"),
            unique=True,
        ),
        Index(
            "ix_product_attribute_options_attribute_order",
            "attribute_id",
            "display_order",
        ),
        CheckConstraint(
            "length(trim(label)) > 0",
            name="ck_product_attribute_options_label_not_blank",
        ),
        CheckConstraint(
            "length(trim(value)) > 0",
            name="ck_product_attribute_options_value_not_blank",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_product_attribute_options_display_order_non_negative",
        ),
    )

    @validates("label", "value")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()
