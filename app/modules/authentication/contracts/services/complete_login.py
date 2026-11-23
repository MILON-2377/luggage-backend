from abc import ABC, abstractmethod

from app.modules.authentication.dtos.complete_login import (
    CompleteLoginRequest,
    CompleteLoginResponse,
)


class AbstractCompleteLoginService(ABC):
    @abstractmethod
    async def complete_login(
        self,
        payload: CompleteLoginRequest,
    ) -> CompleteLoginResponse:
        raise NotImplementedError