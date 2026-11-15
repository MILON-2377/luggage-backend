from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.catalog.enums import AttributeDataType


class ProductAttribute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_attributes"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    data_type: Mapped[AttributeDataType] = mapped_column(
        Enum(
            AttributeDataType,
            name="attribute_data_type",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    is_custom_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_product_attributes_slug",
            "slug",
            unique=True,
        ),
        Index(
            "uq_product_attributes_name_lower",
            text("lower(name)"),
            unique=True,
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_product_attributes_name_not_blank",
        ),
        CheckConstraint(
            "slug = lower(slug) AND slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_product_attributes_slug_format",
        ),
        CheckConstraint(
            "unit IS NULL OR length(trim(unit)) > 0",
            name="ck_product_attributes_unit_not_blank",
        ),
        CheckConstraint(
            "unit IS NULL OR data_type = 'number'",
            name="ck_product_attributes_unit_requires_number",
        ),
        CheckConstraint(
            "NOT is_custom_allowed OR data_type IN ('select', 'multi_select')",
            name="ck_product_attributes_custom_requires_select",
        ),
    )

    @validates("name")
    def _normalize_name(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("slug")
    def _normalize_slug(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("description", "unit")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
