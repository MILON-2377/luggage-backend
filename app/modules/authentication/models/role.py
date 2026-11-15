
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.database.base import Base
from app.core.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_roles_slug",
            "slug",
            unique=True,
        ),
        Index(
            "uq_roles_name_lower",
            text("lower(name)"),
            unique=True,
        ),
        CheckConstraint(
            "slug = lower(slug) AND slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_roles_slug_format",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_roles_name_not_blank",
        ),
    )

    @validates("name")
    def _normalize_name(self, _key: str, value: str) -> str:
        return value.strip()

    @validates("slug")
    def _normalize_slug(self, _key: str, value: str) -> str:
        return value.strip().lower()
