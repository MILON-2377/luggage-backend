
from abc import ABC, abstractmethod

from app.modules.authentication.dtos.passkey_login import (
    PasskeyLoginOptionsRequest,
    PasskeyLoginOptionsResponse,
)


class AbstractPasskeyLoginOptionsService(ABC):
    @abstractmethod
    async def generate_options(
        self,
        payload: PasskeyLoginOptionsRequest,
    ) -> PasskeyLoginOptionsResponse:
        raise NotImplementedError
