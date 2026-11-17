from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.authentication.contracts.repositories.role import (
    AbstractRoleRepository,
)
from app.modules.authentication.models.role import Role


class RoleRepository(
    BaseRepository[Role],
    AbstractRoleRepository,
):
    async def get_by_slug(self, slug: str) -> Role | None:
        statement = select(Role).where(
            Role.slug == slug.strip().lower(),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
