from app.core.config import settings
from app.core.contracts.security.jwt_provider import AbstractJWTProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.jwt_provider import JWTProvider
from app.integrations.security.sha256_token_hasher import (
    SHA256TokenHasher,
)
from app.modules.authentication.contracts.services.token import (
    AbstractAuthenticationTokenService,
)
from app.modules.authentication.services.token import (
    AuthenticationTokenService,
)


def get_authentication_token_service() -> AbstractAuthenticationTokenService:
    jwt_provider: AbstractJWTProvider = JWTProvider(settings=settings)
    token_hasher: TokenHasher = SHA256TokenHasher()

    return AuthenticationTokenService(
        jwt_provider=jwt_provider,
        token_hasher=token_hasher,
        settings=settings,
    )
