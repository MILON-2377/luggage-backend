import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin
from app.modules.catalog.enums import CategoryMediaRole
from app.modules.catalog.models.product_category import ProductCategory
from app.modules.media.models.media_asset import MediaAsset


class CategoryMedia(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "category_media"

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="CASCADE",
            name="fk_category_media_category_id",
        ),
        nullable=False,
    )

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_assets.id",
            ondelete="RESTRICT",
            name="fk_category_media_media_asset_id",
        ),
        nullable=False,
    )

    media_role: Mapped[CategoryMediaRole] = mapped_column(
        Enum(
            CategoryMediaRole,
            name="category_media_role",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        lazy="raise",
    )

    media_asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_category_media_category_asset_role",
            "category_id",
            "media_asset_id",
            "media_role",
            unique=True,
        ),
        Index(
            "ix_category_media_category_order",
            "category_id",
            "display_order",
        ),
        Index(
            "ix_category_media_media_asset_id",
            "media_asset_id",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_category_media_display_order_non_negative",
        ),
    )

    @validates("display_order")
    def _validate_display_order(self, _key: str, value: int) -> int:
        if value < 0:
            raise ValueError("display_order must be non-negative")
        return value