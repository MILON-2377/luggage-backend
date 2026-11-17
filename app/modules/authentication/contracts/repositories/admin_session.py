import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.admin_session import AdminSession


class AbstractAdminSessionRepository(AbstractRepository):
    @abstractmethod
    async def get_by_id(
        self,
        session_id: uuid.UUID,
    ) -> AdminSession | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminSession | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, session: AdminSession) -> None:
        raise NotImplementedError
