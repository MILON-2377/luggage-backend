import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING

from app.modules.quotation.enums.acceptance_method import AcceptanceMethod
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.quotation.models.quotation import Quotation
    from app.modules.quotation.models.quotation_version import QuotationVersion


class QuotationAcceptance(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quotation_acceptances"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotations.id",
            ondelete="RESTRICT",
            name="fk_quotation_acceptances_quotation_id",
        ),
        nullable=False,
    )

    quotation_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotation_versions.id",
            ondelete="RESTRICT",
            name="fk_quotation_acceptances_quotation_version_id",
        ),
        nullable=False,
    )

    accepted_by_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    accepted_by_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    acceptance_method: Mapped[AcceptanceMethod] = mapped_column(
        Enum(
            AcceptanceMethod,
            name="acceptance_method",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=30,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    ip_address: Mapped[IPv4Address | IPv6Address | None] = mapped_column(
        INET,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quotation: Mapped["Quotation"] = relationship(
        "Quotation",
        lazy="raise",
    )

    quotation_version: Mapped["QuotationVersion"] = relationship(
        "QuotationVersion",
        lazy="raise",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["quotation_id", "quotation_version_id"],
            ["quotation_versions.quotation_id", "quotation_versions.id"],
            ondelete="RESTRICT",
            name="fk_quotation_acceptances_version_belongs_to_quotation",
        ),
        Index(
            "uq_quotation_acceptances_quotation_id",
            "quotation_id",
            unique=True,
        ),
        Index(
            "ix_quotation_acceptances_quotation_version_id",
            "quotation_version_id",
        ),
        Index(
            "ix_quotation_acceptances_accepted_by_email_lower",
            text("lower(accepted_by_email)"),
        ),
        CheckConstraint(
            "length(trim(accepted_by_name)) > 0",
            name="ck_quotation_acceptances_accepted_by_name_not_blank",
        ),
        CheckConstraint(
            "accepted_by_email = lower(accepted_by_email) "
            "AND accepted_by_email ~ '^[^@\\s]+@[^@\\s]+$'",
            name="ck_quotation_acceptances_email_format",
        ),
    )

    @validates("accepted_by_name")
    def _strip_name(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("accepted_by_email")
    def _normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("user_agent")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None