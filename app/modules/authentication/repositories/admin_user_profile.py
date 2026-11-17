import uuid

from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.admin_user_profile import (
    AbstractAdminUserProfileRepository,
)
from app.modules.authentication.models.admin_user_profile import AdminUserProfile


class AdminUserProfileRepository(
    BaseRepository[AdminUserProfile],
    AbstractAdminUserProfileRepository,
):
    async def get_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> AdminUserProfile | None:
        statement = select(AdminUserProfile).where(
            AdminUserProfile.admin_user_id == admin_user_id,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
