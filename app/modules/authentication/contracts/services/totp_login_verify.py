from abc import ABC, abstractmethod

from app.modules.authentication.dtos.complete_login import CompleteLoginResponse
from app.modules.authentication.dtos.totp_login_verify import (
    TotpLoginVerifyRequest,
)


class AbstractTotpLoginVerifyService(ABC):
    @abstractmethod
    async def verify(
        self,
        payload: TotpLoginVerifyRequest,
    ) -> CompleteLoginResponse:
        raise NotImplementedError