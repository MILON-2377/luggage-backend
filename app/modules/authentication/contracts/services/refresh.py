from abc import ABC, abstractmethod

from app.modules.authentication.dtos.refresh import RefreshTokensDTO


class AbstractRefreshService(ABC):
    @abstractmethod
    async def refresh(
        self,
        refresh_token: str,
    ) -> RefreshTokensDTO:
        raise NotImplementedError
