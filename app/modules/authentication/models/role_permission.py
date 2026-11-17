import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base

if TYPE_CHECKING:
    from app.modules.authentication.models.permission import Permission
    from app.modules.authentication.models.role import Role


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "roles.id",
            ondelete="CASCADE",
            name="fk_role_permissions_role_id",
        ),
        primary_key=True,
    )

    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
            name="fk_role_permissions_permission_id",
        ),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    role: Mapped["Role"] = relationship(
        "Role",
        lazy="raise",
    )

    permission: Mapped["Permission"] = relationship(
        "Permission",
        lazy="raise",
    )

    __table_args__ = (
        Index(
            "ix_role_permissions_permission_id",
            "permission_id",
        ),
    )
