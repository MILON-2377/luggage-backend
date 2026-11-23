from abc import ABC, abstractmethod

from app.modules.authentication.dtos.complete_login import (
    CompleteLoginResponse,
)
from app.modules.authentication.dtos.passkey_login_verify import (
    PasskeyLoginVerifyRequest,
)


class AbstractPasskeyLoginVerifyService(ABC):
    @abstractmethod
    async def verify(
        self,
        payload: PasskeyLoginVerifyRequest,
    ) -> CompleteLoginResponse:
        raise NotImplementedError