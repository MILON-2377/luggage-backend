import uuid

from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.user_role import (
    AbstractUserRoleRepository,
)
from app.modules.authentication.models.user_role import UserRole


class UserRoleRepository(
    BaseRepository[UserRole],
    AbstractUserRoleRepository,
):
    async def get_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> list[UserRole]:
        statement = select(UserRole).where(
            UserRole.admin_user_id == admin_user_id,
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())
