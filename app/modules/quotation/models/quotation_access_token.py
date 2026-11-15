import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin
from app.modules.quotation.models.quotation import Quotation


class QuotationAccessToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quotation_access_tokens"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "quotations.id",
            ondelete="CASCADE",
            name="fk_quotation_access_tokens_quotation_id",
        ),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quotation: Mapped["Quotation"] = relationship(
        "Quotation",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_quotation_access_tokens_token_hash",
            "token_hash",
            unique=True,
        ),
        Index(
            "ix_quotation_access_tokens_active_by_quotation",
            "quotation_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index(
            "ix_quotation_access_tokens_expires_at",
            "expires_at",
        ),
        CheckConstraint(
            "token_hash ~ '^[a-f0-9]{64}$'",
            name="ck_quotation_access_tokens_token_hash_format",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_quotation_access_tokens_expires_after_created",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_quotation_access_tokens_revoked_after_created",
        ),
    )
