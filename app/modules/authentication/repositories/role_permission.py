import uuid
from collections.abc import Iterable
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.role_permission import (
    AbstractRolePermissionRepository,
)
from app.modules.authentication.models.role_permission import RolePermission


class RolePermissionRepository(
    BaseRepository[RolePermission],
    AbstractRolePermissionRepository,
):
    async def get_by_role_id(
        self,
        role_id: uuid.UUID,
    ) -> list[RolePermission]:
        statement = (
            select(RolePermission)
            .where(RolePermission.role_id == role_id)
            .order_by(RolePermission.permission_id)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_permission_ids_by_role_id(
        self,
        role_id: uuid.UUID,
    ) -> set[uuid.UUID]:
        statement = select(RolePermission.permission_id).where(
            RolePermission.role_id == role_id,
        )

        result = await self.session.execute(statement)
        return set(result.scalars().all())

    async def exists(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> bool:
        statement = (
            select(RolePermission.role_id)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            .limit(1)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def add_many(
        self,
        role_id: uuid.UUID,
        permission_ids: Iterable[uuid.UUID],
    ) -> int:
        values = [
            {"role_id": role_id, "permission_id": permission_id}
            for permission_id in set(permission_ids)
        ]

        if not values:
            return 0

        statement = (
            pg_insert(RolePermission)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[
                    RolePermission.role_id,
                    RolePermission.permission_id,
                ]
            )
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount

    async def remove_many(
        self,
        role_id: uuid.UUID,
        permission_ids: Iterable[uuid.UUID],
    ) -> int:
        ids = set(permission_ids)

        if not ids:
            return 0

        statement = (
            delete(RolePermission)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id.in_(ids),
            )
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(statement)
        return cast(CursorResult, result).rowcount

    async def replace_for_role(
        self,
        role_id: uuid.UUID,
        permission_ids: Iterable[uuid.UUID],
    ) -> None:
        target = set(permission_ids)
        current = await self.get_permission_ids_by_role_id(role_id)

        await self.remove_many(role_id, current - target)
        await self.add_many(role_id, target - current)
