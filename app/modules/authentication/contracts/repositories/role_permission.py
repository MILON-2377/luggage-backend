import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.role_permission import RolePermission


class AbstractRolePermissionRepository(AbstractRepository):
    @abstractmethod
    async def get_by_role_id(
        self,
        role_id: uuid.UUID,
    ) -> list[RolePermission]:
        raise NotImplementedError

    @abstractmethod
    def create(self, role_permission: RolePermission) -> None:
        raise NotImplementedError
