from abc import abstractmethod

from app.core.contracts.services.service import AbstractService
from app.modules.authentication.dtos.accept_invitation import (
    AcceptInvitationDTO,
)


class AbstractInvitationAcceptanceService(AbstractService):
    @abstractmethod
    async def accept_invitation(
        self,
        data: AcceptInvitationDTO,
    ) -> None:
        raise NotImplementedError
