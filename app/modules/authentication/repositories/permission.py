import uuid
from collections.abc import Iterable

from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.permission import (
    AbstractPermissionRepository,
)
from app.modules.authentication.models.permission import Permission
from app.modules.authentication.models.role_permission import RolePermission
from app.modules.authentication.models.user_role import UserRole


class PermissionRepository(
    BaseRepository[Permission],
    AbstractPermissionRepository,
):
    async def get_by_code(self, code: str) -> Permission | None:
        statement = select(Permission).where(
            Permission.code == code.strip().lower(),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_codes(self, codes: Iterable[str]) -> list[Permission]:
        normalized_codes = {code.strip().lower() for code in codes}

        if not normalized_codes:
            return []

        statement = (
            select(Permission)
            .where(Permission.code.in_(normalized_codes))
            .order_by(Permission.code)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_role_id(self, role_id: uuid.UUID) -> list[Permission]:
        statement = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.code)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_codes_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> set[str]:
        statement = (
            select(Permission.code)
            .distinct()
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.admin_user_id == admin_user_id)
        )

        result = await self.session.execute(statement)
        return set(result.scalars().all())
