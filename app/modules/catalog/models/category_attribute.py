import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product_attribute import ProductAttribute
    from app.modules.catalog.models.product_category import ProductCategory


class CategoryAttribute(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "category_attributes"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="CASCADE",
            name="fk_category_attributes_category_id",
        ),
        nullable=False,
    )

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_attributes.id",
            ondelete="RESTRICT",
            name="fk_category_attributes_attribute_id",
        ),
        nullable=False,
    )

    is_required: Mapped[bool] = mapped_column(
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        back_populates="category_attributes",
        lazy="raise",
    )

    attribute: Mapped["ProductAttribute"] = relationship(
        "ProductAttribute",
        back_populates="category_attributes",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_category_attributes_category_attribute",
            "category_id",
            "attribute_id",
            unique=True,
        ),
        Index(
            "ix_category_attributes_category_order",
            "category_id",
            "display_order",
        ),
        Index(
            "ix_category_attributes_attribute_id",
            "attribute_id",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_category_attributes_display_order_non_negative",
        ),
    )
