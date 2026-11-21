from abc import ABC, abstractmethod

from app.modules.authentication.dtos.initial_mfa_setup_authorization import (
    InitialMFASetupAuthorizationResult,
)


class AbstractInitialMFASetupAuthorizationService(ABC):
    @abstractmethod
    async def authorize_initial_setup(
        self,
        initial_setup_token: str,
    ) -> InitialMFASetupAuthorizationResult:
        raise NotImplementedError
