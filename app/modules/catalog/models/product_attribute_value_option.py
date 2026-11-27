import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Index,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.catalog.models.product_attribute_option import (
        ProductAttributeOption,
    )
    from app.modules.catalog.models.product_attribute_value import (
        ProductAttributeValue,
    )


class ProductAttributeValueOption(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_attribute_value_options"

    product_attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_attribute_values.id",
            ondelete="CASCADE",
            name="fk_product_attribute_value_options_value_id",
        ),
        nullable=False,
    )

    option_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_attribute_options.id",
            ondelete="RESTRICT",
            name="fk_product_attribute_value_options_option_id",
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    product_attribute_value: Mapped["ProductAttributeValue"] = relationship(
        "ProductAttributeValue",
        back_populates="selected_options",
        lazy="raise",
    )

    option: Mapped["ProductAttributeOption"] = relationship(
        "ProductAttributeOption",
        back_populates="product_value_options",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_attribute_value_options_value_option",
            "product_attribute_value_id",
            "option_id",
            unique=True,
        ),
        Index(
            "ix_product_attribute_value_options_option_id",
            "option_id",
        ),
    )
