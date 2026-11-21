import uuid
from abc import abstractmethod
from datetime import datetime

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.auth_recovery_code import AuthRecoveryCode


class AbstractAuthRecoveryCodeRepository(AbstractRepository):
    @abstractmethod
    async def get_available_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> list[AuthRecoveryCode]:
        raise NotImplementedError

    @abstractmethod
    async def get_available_by_code_hash(
        self,
        admin_user_id: uuid.UUID,
        code_hash: str,
        *,
        for_update: bool = False,
    ) -> AuthRecoveryCode | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, recovery_code: AuthRecoveryCode) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_all_available_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        revoked_at: datetime,
    ) -> int:
        raise NotImplementedError
