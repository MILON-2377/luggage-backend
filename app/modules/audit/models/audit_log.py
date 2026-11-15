import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"

    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_audit_logs_admin_user_id",
        ),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
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

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    admin_user: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[admin_user_id],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_audit_logs_resource_created_at",
            "resource_type",
            "resource_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_audit_logs_admin_user_created_at",
            "admin_user_id",
            text("created_at DESC"),
            postgresql_where=text("admin_user_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_logs_action_created_at",
            "action",
            text("created_at DESC"),
        ),
        Index(
            "ix_audit_logs_created_at_brin",
            "created_at",
            postgresql_using="brin",
        ),
        Index(
            "ix_audit_logs_request_id",
            "request_id",
            postgresql_where=text("request_id IS NOT NULL"),
        ),
        CheckConstraint(
            "action ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_audit_logs_action_format",
        ),
        CheckConstraint(
            "length(trim(resource_type)) > 0",
            name="ck_audit_logs_resource_type_not_blank",
        ),
        CheckConstraint(
            "old_values IS NULL OR jsonb_typeof(old_values) = 'object'",
            name="ck_audit_logs_old_values_is_object",
        ),
        CheckConstraint(
            "new_values IS NULL OR jsonb_typeof(new_values) = 'object'",
            name="ck_audit_logs_new_values_is_object",
        ),
    )

    @validates("action", "resource_type")
    def _normalize_identifier(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("description", "user_agent", "request_id")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
