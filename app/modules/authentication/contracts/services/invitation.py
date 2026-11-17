import uuid
from abc import abstractmethod

from app.core.contracts.services.service import AbstractService
from app.modules.authentication.dtos.invitation import InvitationResultDTO
from app.modules.authentication.dtos.validate_invitation import (
    ValidateInvitationDTO,
)


class AbstractInvitationService(AbstractService):
    @abstractmethod
    async def create_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> InvitationResultDTO:
        raise NotImplementedError

    @abstractmethod
    async def validate_invitation(
        self,
        token: str,
    ) -> ValidateInvitationDTO:
        raise NotImplementedError

    @abstractmethod
    async def resend_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> InvitationResultDTO:
        raise NotImplementedError

    @abstractmethod
    async def revoke_invitation(
        self,
        admin_user_id: uuid.UUID,
    ) -> None:
        raise NotImplementedError
