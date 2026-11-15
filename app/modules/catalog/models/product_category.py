import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
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
from app.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.core.enums.record_status import RecordStatus


class ProductCategory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "product_categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
            name="fk_product_categories_parent_id",
        ),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
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
        server_default=text("'draft'"),
        nullable=False,
    )

    parent: Mapped["ProductCategory | None"] = relationship(
        "ProductCategory",
        remote_side="ProductCategory.id",
        back_populates="children",
        lazy="raise",
    )

    children: Mapped[list["ProductCategory"]] = relationship(
        "ProductCategory",
        back_populates="parent",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_categories_parent_slug_active",
            text("coalesce(parent_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_product_categories_parent_order_active",
            "parent_id",
            "display_order",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_product_categories_status_active",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_product_categories_not_own_parent",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_product_categories_name_not_blank",
        ),
        CheckConstraint(
            "slug = lower(slug) AND slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_product_categories_slug_format",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_product_categories_display_order_non_negative",
        ),
    )

    @validates("name")
    def _normalize_name(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("slug")
    def _normalize_slug(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("description")
    def _normalize_description(
        self,
        _key: str,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return value.strip() or None
