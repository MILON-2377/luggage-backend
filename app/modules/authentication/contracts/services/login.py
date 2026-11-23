from abc import ABC, abstractmethod

from app.modules.authentication.dtos.login import (
    LoginRequest,
    LoginResponse,
)


class AbstractLoginService(ABC):
    @abstractmethod
    async def login(
        self,
        payload: LoginRequest,
    ) -> LoginResponse:
        raise NotImplementedError