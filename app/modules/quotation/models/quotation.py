import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
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
from app.modules.authentication.models.admin_user import AdminUser
from app.modules.inquiry.models.inquiry import Inquiry
from app.modules.quotation.enums.quotation_status import QuotationStatus

if TYPE_CHECKING:
    from app.modules.quotation.models.quotation_version import QuotationVersion


class Quotation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "quotations"

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "inquiries.id",
            ondelete="RESTRICT",
            name="fk_quotations_inquiry_id",
        ),
        nullable=False,
    )

    quotation_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[QuotationStatus] = mapped_column(
        Enum(
            QuotationStatus,
            name="quotation_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=QuotationStatus.DRAFT,
        server_default=QuotationStatus.DRAFT.value,
        nullable=False,
    )

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotation_versions.id",
            ondelete="SET NULL",
            name="fk_quotations_current_version_id",
            use_alter=True,
        ),
        nullable=True,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_quotations_created_by",
        ),
        nullable=True,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_quotations_updated_by",
        ),
        nullable=True,
    )

    inquiry: Mapped["Inquiry"] = relationship(
        "Inquiry",
        lazy="raise",
    )

    current_version: Mapped["QuotationVersion | None"] = relationship(
        "QuotationVersion",
        foreign_keys=[current_version_id],
        post_update=True,
        lazy="raise",
    )

    creator: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[created_by],
        lazy="raise",
    )

    updater: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[updated_by],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_quotations_quotation_number",
            "quotation_number",
            unique=True,
        ),
        Index(
            "ix_quotations_inquiry_created_at_active",
            "inquiry_id",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_quotations_active_status_created_at",
            "status",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_quotations_sent_valid_until",
            "valid_until",
            postgresql_where=text(
                "status = 'sent' AND valid_until IS NOT NULL AND deleted_at IS NULL"
            ),
        ),
        Index(
            "ix_quotations_current_version_id",
            "current_version_id",
            postgresql_where=text("current_version_id IS NOT NULL"),
        ),
        Index(
            "ix_quotations_created_by",
            "created_by",
            postgresql_where=text("created_by IS NOT NULL"),
        ),
        Index(
            "ix_quotations_updated_by",
            "updated_by",
            postgresql_where=text("updated_by IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(quotation_number)) > 0",
            name="ck_quotations_quotation_number_not_blank",
        ),
        CheckConstraint(
            "status IN ('draft', 'cancelled') OR current_version_id IS NOT NULL",
            name="ck_quotations_non_draft_requires_version",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until > created_at",
            name="ck_quotations_valid_until_after_created",
        ),
    )

    @validates("quotation_number")
    def _strip_quotation_number(self, _key: str, value: str) -> str:
        return value.strip()
