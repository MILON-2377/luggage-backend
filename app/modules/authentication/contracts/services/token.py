from abc import ABC, abstractmethod

from app.modules.authentication.dtos.token import (
    AuthenticationTokensDTO,
    CreateAuthenticationTokensRequest,
)


class AbstractAuthenticationTokenService(ABC):
    @abstractmethod
    def create_tokens(
        self,
        payload: CreateAuthenticationTokensRequest,
    ) -> AuthenticationTokensDTO:
        raise NotImplementedError