from abc import abstractmethod

from app.core.contracts.services.service import AbstractService
from app.modules.authentication.dtos.account_provisioning import (
    CreateInvitedAccountDTO,
)
from app.modules.authentication.dtos.invitation import InvitationResultDTO


class AbstractAccountProvisioningService(AbstractService):
    @abstractmethod
    async def create_invited_account(
        self,
        data: CreateInvitedAccountDTO,
    ) -> InvitationResultDTO:
        raise NotImplementedError
