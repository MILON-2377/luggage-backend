import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.user_role import UserRole


class AbstractUserRoleRepository(AbstractRepository):
    @abstractmethod
    async def get_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> list[UserRole]:
        raise NotImplementedError

    @abstractmethod
    def create(self, user_role: UserRole) -> None:
        raise NotImplementedError
