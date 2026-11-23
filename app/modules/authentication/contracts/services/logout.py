from abc import ABC, abstractmethod

from app.modules.authentication.dtos.logout import LogoutResponse


class AbstractLogoutService(ABC):
    @abstractmethod
    async def logout(
        self,
        refresh_token: str | None,
    ) -> LogoutResponse:
        raise NotImplementedError