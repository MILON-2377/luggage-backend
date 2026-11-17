import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.admin_user_profile import AdminUserProfile


class AbstractAdminUserProfileRepository(AbstractRepository):
    @abstractmethod
    async def get_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> AdminUserProfile | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, profile: AdminUserProfile) -> None:
        raise NotImplementedError
