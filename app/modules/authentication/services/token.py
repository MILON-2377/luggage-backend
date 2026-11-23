import secrets
from datetime import timedelta

from app.core.config import Settings
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.jwt_provider import JWTProvider
from app.modules.authentication.contracts.services.token import (
    AbstractAuthenticationTokenService,
)
from app.modules.authentication.dtos.token import (
    AuthenticationTokensDTO,
    CreateAuthenticationTokensRequest,
)


class AuthenticationTokenService(AbstractAuthenticationTokenService):
    def __init__(
        self,
        jwt_provider: JWTProvider,
        token_hasher: TokenHasher,
        settings: Settings,
    ) -> None:
        self.jwt_provider = jwt_provider
        self.token_hasher = token_hasher
        self.settings = settings

    def create_tokens(
        self,
        payload: CreateAuthenticationTokensRequest,
    ) -> AuthenticationTokensDTO:
        access_token = self.jwt_provider.create_access_token(
            user_id=payload.admin_user_id,
            session_id=payload.session_id,
        )

        refresh_token = secrets.token_urlsafe(64)
        refresh_token_hash = self.token_hasher.hash_token(refresh_token)

        access_token_expires_at = payload.issued_at + timedelta(
            minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

        session_expires_at = payload.issued_at + timedelta(
            days=self.settings.AUTH_SESSION_EXPIRE_DAYS
        )

        return AuthenticationTokensDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_hash=refresh_token_hash,
            access_token_expires_at=access_token_expires_at,
            session_expires_at=session_expires_at,
        )