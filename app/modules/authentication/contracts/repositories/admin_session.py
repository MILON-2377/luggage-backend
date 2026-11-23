import uuid
from abc import abstractmethod
from datetime import datetime

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.enums import SessionRevocationReason
from app.modules.authentication.models.admin_session import AdminSession


class AbstractAdminSessionRepository(AbstractRepository):
    @abstractmethod
    async def get_by_id(
        self,
        session_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminSession | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_refresh_token_hash(
        self,
        refresh_token_hash: str,
        *,
        for_update: bool = False,
    ) -> AdminSession | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        now: datetime,
        *,
        for_update: bool = False,
    ) -> list[AdminSession]:
        raise NotImplementedError

    @abstractmethod
    def create(self, session: AdminSession) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke(
        self,
        session_id: uuid.UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def revoke_all_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        revoked_at: datetime,
        reason: SessionRevocationReason,
        *,
        except_session_id: uuid.UUID | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def touch_last_activity(
        self,
        session_id: uuid.UUID,
        now: datetime,
    ) -> bool:
        raise NotImplementedError