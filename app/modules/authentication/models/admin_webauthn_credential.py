import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class AdminWebauthnCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_webauthn_credentials"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_admin_webauthn_credentials_admin_user_id",
        ),
        nullable=False,
    )

    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    public_key: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    sign_count: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    transports: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(20)),
        nullable=True,
    )

    aaguid: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    backup_eligible: Mapped[bool] = mapped_column(
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    backup_state: Mapped[bool] = mapped_column(
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
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
            "uq_admin_webauthn_credentials_credential_id",
            "credential_id",
            unique=True,
        ),
        Index(
            "ix_admin_webauthn_credentials_admin_user_id",
            "admin_user_id",
        ),
        Index(
            "ix_admin_webauthn_credentials_active_by_user",
            "admin_user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        CheckConstraint(
            "sign_count >= 0",
            name="ck_admin_webauthn_credentials_sign_count_non_negative",
        ),
        CheckConstraint(
            "octet_length(credential_id) BETWEEN 16 AND 1023",
            name="ck_admin_webauthn_credentials_credential_id_length",
        ),
        CheckConstraint(
            "backup_state = false OR backup_eligible = true",
            name="ck_admin_webauthn_credentials_backup_state_requires_eligible",
        ),
    )