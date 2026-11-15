import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
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
from app.core.enums.record_status import RecordStatus
from app.modules.catalog.models.product_category import ProductCategory


class Product(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "products"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
            name="fk_products_category_id",
        ),
        nullable=False,
    )

    product_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(280),
        nullable=False,
    )

    short_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starting_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    minimum_order_quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
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
        server_default=text("'draft'"),
        nullable=False,
    )

    is_featured: Mapped[bool] = mapped_column(
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

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_products_created_by",
        ),
        nullable=True,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_products_updated_by",
        ),
        nullable=True,
    )

    category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_products_product_code_lower_active",
            text("lower(product_code)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_products_slug_active",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_category_order_active",
            "category_id",
            "display_order",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_status_published_at_active",
            "status",
            text("published_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_featured_active",
            "display_order",
            postgresql_where=text(
                "is_featured AND status = 'published' AND deleted_at IS NULL"
            ),
        ),
        Index(
            "ix_products_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        Index(
            "ix_products_updated_by",
            "updated_by",
            postgresql_where=text("updated_by IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(product_code)) > 0",
            name="ck_products_product_code_not_blank",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_products_name_not_blank",
        ),
        CheckConstraint(
            "slug = lower(slug) AND slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_products_slug_format",
        ),
        CheckConstraint(
            "starting_price IS NULL OR starting_price >= 0",
            name="ck_products_starting_price_non_negative",
        ),
        CheckConstraint(
            "currency IS NULL OR currency ~ '^[A-Z]{3}$'",
            name="ck_products_currency_format",
        ),
        CheckConstraint(
            "(starting_price IS NULL) = (currency IS NULL)",
            name="ck_products_price_currency_together",
        ),
        CheckConstraint(
            "minimum_order_quantity > 0",
            name="ck_products_minimum_order_quantity_positive",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_products_display_order_non_negative",
        ),
        CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name="ck_products_published_requires_published_at",
        ),
    )

    @validates("product_code", "name")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("slug")
    def _normalize_slug(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("currency")
    def _normalize_currency(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper() or None

    @validates("short_description", "description")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
