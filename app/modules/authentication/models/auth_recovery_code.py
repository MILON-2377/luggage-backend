
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class AuthRecoveryCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "auth_recovery_codes"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_auth_recovery_codes_admin_user_id",
        ),
        nullable=False,
    )

    code_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_auth_recovery_codes_admin_user_id_code_hash",
            "admin_user_id",
            "code_hash",
            unique=True,
        ),
        Index(
            "ix_auth_recovery_codes_available_by_user",
            "admin_user_id",
            postgresql_where=text(
                "used_at IS NULL AND revoked_at IS NULL"
            ),
        ),
        CheckConstraint(
            "used_at IS NULL OR revoked_at IS NULL",
            name="ck_auth_recovery_codes_not_used_and_revoked",
        ),
    )
