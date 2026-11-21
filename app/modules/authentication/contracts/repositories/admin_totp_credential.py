import uuid
from abc import abstractmethod
from datetime import datetime

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.admin_totp_credential import (
    AdminTotpCredential,
)


class AbstractAdminTotpCredentialRepository(AbstractRepository):
    @abstractmethod
    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminTotpCredential | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, credential: AdminTotpCredential) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_unrevoked_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> AdminTotpCredential | None:
        raise NotImplementedError

    @abstractmethod
    async def mark_verified(
        self,
        credential_id: uuid.UUID,
        verified_at: datetime,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def record_successful_use(
        self,
        credential_id: uuid.UUID,
        time_step: int,
        used_at: datetime,
    ) -> bool:
        raise NotImplementedError
