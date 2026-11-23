from abc import ABC, abstractmethod

from app.modules.authentication.dtos.session import (
    CreateAdminSessionRequest,
    CreateAdminSessionResponse,
)


class AbstractAdminSessionService(ABC):
    @abstractmethod
    async def create_session(
        self,
        payload: CreateAdminSessionRequest,
    ) -> CreateAdminSessionResponse:
        raise NotImplementedError