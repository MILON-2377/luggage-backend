import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base

if TYPE_CHECKING:
    from app.modules.authentication.models.admin_user import AdminUser
    from app.modules.authentication.models.role import Role


class UserRole(Base):
    __tablename__ = "user_roles"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="CASCADE",
            name="fk_user_roles_admin_user_id",
        ),
        primary_key=True,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "roles.id",
            ondelete="RESTRICT",
            name="fk_user_roles_role_id",
        ),
        primary_key=True,
    )

    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
            name="fk_user_roles_assigned_by",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        foreign_keys="UserRole.admin_user_id",
        lazy="raise",
    )

    role: Mapped["Role"] = relationship(
        "Role",
        lazy="raise",
    )

    assigned_by_user: Mapped["AdminUser | None"] = relationship(
        "AdminUser",
        foreign_keys="UserRole.assigned_by",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_user_roles_role_id",
            "role_id",
        ),
        Index(
            "ix_user_roles_assigned_by",
            "assigned_by",
        ),
    )
