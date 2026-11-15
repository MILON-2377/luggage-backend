from sqlalchemy import (
    CheckConstraint,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resource: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_permissions_code",
            "code",
            unique=True,
        ),
        Index(
            "ix_permissions_resource",
            "resource",
        ),
        Index(
            "uq_permissions_resource_action",
            "resource",
            "action",
            unique=True,
        ),
        CheckConstraint(
            "code = resource || ':' || action",
            name="ck_permissions_code_matches_resource_action",
        ),
        CheckConstraint(
            "resource ~ '^[a-z][a-z0-9_]*$' "
            "AND action ~ '^[a-z][a-z0-9_]*$'",
            name="ck_permissions_resource_action_format",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_permissions_name_not_blank",
        ),
    )

    @validates("code", "resource", "action")
    def _normalize_identifier(self, _key: str, value: str) -> str:
        return value.strip().lower()

    @validates("name")
    def _normalize_name(self, _key: str, value: str) -> str:
        return value.strip()