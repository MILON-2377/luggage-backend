import uuid
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.modules.inquiry.enums import InquirySource, InquiryStatus

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class Inquiry(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "inquiries"

    inquiry_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    company_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[InquiryStatus] = mapped_column(
        Enum(
            InquiryStatus,
            name="inquiry_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        default=InquiryStatus.NEW,
        server_default=InquiryStatus.NEW.value,
        nullable=False,
    )

    source: Mapped[InquirySource] = mapped_column(
        Enum(
            InquirySource,
            name="inquiry_source",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=50,
            create_constraint=True,
            validate_strings=True,
        ),
        default=InquirySource.CONTACT_FORM,
        server_default=InquirySource.CONTACT_FORM.value,
        nullable=False,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_inquiries_assigned_to",
        ),
        nullable=True,
    )

    ip_address: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assignee: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[assigned_to],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_inquiries_inquiry_number",
            "inquiry_number",
            unique=True,
        ),
        Index(
            "ix_inquiries_active_status_created_at",
            "status",
            text("created_at DESC"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_inquiries_assigned_to_active",
            "assigned_to",
            "status",
            postgresql_where=text("assigned_to IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index(
            "ix_inquiries_email_lower",
            text("lower(email)"),
        ),
        Index(
            "ix_inquiries_ip_address_created_at",
            "ip_address",
            "created_at",
            postgresql_where=text("ip_address IS NOT NULL"),
        ),
        CheckConstraint(
            "length(trim(inquiry_number)) > 0",
            name="ck_inquiries_inquiry_number_not_blank",
        ),
        CheckConstraint(
            "length(trim(customer_name)) > 0",
            name="ck_inquiries_customer_name_not_blank",
        ),
        CheckConstraint(
            "email = lower(email) AND email ~ '^[^@\\s]+@[^@\\s]+$'",
            name="ck_inquiries_email_format",
        ),
        CheckConstraint(
            "length(trim(message)) > 0",
            name="ck_inquiries_message_not_blank",
        ),
    )

    @validates("inquiry_number", "customer_name")
    def _strip_required(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("message")
    def _strip_message(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("company_name", "phone", "country", "subject", "user_agent")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
