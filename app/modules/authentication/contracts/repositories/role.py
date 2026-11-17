from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.role import Role


class AbstractRoleRepository(AbstractRepository):
    @abstractmethod
    async def get_by_slug(
        self,
        slug: str,
    ) -> Role | None:
        raise NotImplementedError
