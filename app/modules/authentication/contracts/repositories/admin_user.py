import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.admin_user import AdminUser


class AbstractAdminUserRepository(AbstractRepository):
    @abstractmethod
    async def get_by_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminUser | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
        *,
        for_update: bool = False,
    ) -> AdminUser | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, admin_user: AdminUser) -> None:
        raise NotImplementedError

    @abstractmethod
    async def acquire_super_admin_bootstrap_lock(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def has_super_admin(self) -> bool:
        raise NotImplementedError
