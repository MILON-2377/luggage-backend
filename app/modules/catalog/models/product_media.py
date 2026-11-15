import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
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
from app.modules.catalog.enums import ProductMediaRole

if TYPE_CHECKING:
    from app.modules.catalog.models.product import Product
    from app.modules.media.models.media_asset import MediaAsset


class ProductMedia(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "product_media"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
            name="fk_product_media_product_id",
        ),
        nullable=False,
    )

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_assets.id",
            ondelete="RESTRICT",
            name="fk_product_media_media_asset_id",
        ),
        nullable=False,
    )

    media_role: Mapped[ProductMediaRole] = mapped_column(
        Enum(
            ProductMediaRole,
            name="product_media_role",
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="media",
        lazy="raise",
    )

    media_asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_product_media_product_asset_role",
            "product_id",
            "media_asset_id",
            "media_role",
            unique=True,
        ),
        Index(
            "uq_product_media_single_primary",
            "product_id",
            unique=True,
            postgresql_where=text("media_role = 'primary'"),
        ),
        Index(
            "ix_product_media_product_role_order",
            "product_id",
            "media_role",
            "display_order",
        ),
        Index(
            "ix_product_media_media_asset_id",
            "media_asset_id",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_product_media_display_order_non_negative",
        ),
    )
