import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.inquiry.models.inquiry import Inquiry
    from app.modules.media.models.media_asset import MediaAsset


class InquiryAttachment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inquiry_attachments"

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "inquiries.id",
            ondelete="CASCADE",
            name="fk_inquiry_attachments_inquiry_id",
        ),
        nullable=False,
    )

    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "media_assets.id",
            ondelete="RESTRICT",
            name="fk_inquiry_attachments_media_asset_id",
        ),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    inquiry: Mapped["Inquiry"] = relationship(
        "Inquiry",
        back_populates="attachments",
        lazy="raise",
    )

    media_asset: Mapped["MediaAsset"] = relationship(
        "MediaAsset",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_inquiry_attachments_inquiry_asset",
            "inquiry_id",
            "media_asset_id",
            unique=True,
        ),
        Index(
            "ix_inquiry_attachments_media_asset_id",
            "media_asset_id",
        ),
        CheckConstraint(
            "length(trim(file_name)) > 0",
            name="ck_inquiry_attachments_file_name_not_blank",
        ),
    )

    @validates("file_name")
    def _strip_file_name(self, _key: str, value: str) -> str:
        return value.strip()
