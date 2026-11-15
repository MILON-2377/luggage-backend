import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    value: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_system_settings_updated_by",
        ),
        nullable=True,
    )

    updater: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys=[updated_by],
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "uq_system_settings_key",
            "key",
            unique=True,
        ),
        Index(
            "ix_system_settings_category",
            "category",
        ),
        Index(
            "ix_system_settings_public_key",
            "key",
            postgresql_where=text("is_public"),
        ),
        Index(
            "ix_system_settings_updated_by",
            "updated_by",
            postgresql_where=text("updated_by IS NOT NULL"),
        ),
        CheckConstraint(
            "key ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$'",
            name="ck_system_settings_key_format",
        ),
        CheckConstraint(
            "category ~ '^[a-z][a-z0-9_]*$'",
            name="ck_system_settings_category_format",
        ),
    )

    @validates("key", "category")
    def _normalize_identifier(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("description")
    def _strip_optional(self, _key: str, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
