from abc import ABC, abstractmethod

from app.modules.authentication.dtos.complete_login import CompleteLoginResponse
from app.modules.authentication.dtos.recovery_code_login_verify import (
    RecoveryCodeLoginVerifyRequest,
)


class AbstractRecoveryCodeLoginVerifyService(ABC):
    @abstractmethod
    async def verify(
        self,
        payload: RecoveryCodeLoginVerifyRequest,
    ) -> CompleteLoginResponse:
        raise NotImplementedError