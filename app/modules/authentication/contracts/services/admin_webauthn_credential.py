import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.authentication.models.admin_webauthn_credential import (
    AdminWebauthnCredential,
)


class AbstractAdminWebauthnCredentialRepository(AbstractRepository):
    @abstractmethod
    async def get_by_credential_id(
        self,
        credential_id: bytes,
        *,
        for_update: bool = False,
    ) -> AdminWebauthnCredential | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_admin_user_id(
        self,
        admin_user_id: uuid.UUID,
    ) -> list[AdminWebauthnCredential]:
        raise NotImplementedError

    @abstractmethod
    def create(self, credential: AdminWebauthnCredential) -> None:
        raise NotImplementedError
