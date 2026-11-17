import uuid

from sqlalchemy import func, select, text

from app.core.constants.security import SUPER_ADMIN_BOOTSTRAP_LOCK_KEY
from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.admin_user import (
    AbstractAdminUserRepository,
)
from app.modules.authentication.enums import RoleType
from app.modules.authentication.models import Role, UserRole
from app.modules.authentication.models.admin_user import AdminUser


class AdminUserRepository(
    BaseRepository[AdminUser],
    AbstractAdminUserRepository,
):
    async def get_by_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminUser | None:
        statement = select(AdminUser).where(
            AdminUser.id == admin_user_id,
            AdminUser.deleted_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        email: str,
        *,
        for_update: bool = False,
    ) -> AdminUser | None:
        statement = select(AdminUser).where(
            func.lower(AdminUser.email) == email.strip().lower(),
            AdminUser.deleted_at.is_(None),
        )

        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def acquire_super_admin_bootstrap_lock(self) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": SUPER_ADMIN_BOOTSTRAP_LOCK_KEY},
        )

    async def has_super_admin(self) -> bool:
        statement = (
            select(UserRole.admin_user_id)
            .join(Role, Role.id == UserRole.role_id)
            .join(AdminUser, AdminUser.id == UserRole.admin_user_id)
            .where(
                Role.slug == RoleType.SUPER_ADMIN.value,
                AdminUser.deleted_at.is_(None),
            )
            .limit(1)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None
