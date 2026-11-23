from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.jwt_provider import AbstractJWTProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.jwt_provider import JWTProvider
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.contracts.services.refresh import (
    AbstractRefreshService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.refresh import RefreshService


def get_refresh_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractRefreshService:
    jwt_provider: AbstractJWTProvider = JWTProvider(settings=settings)
    token_hasher: TokenHasher = SHA256TokenHasher()

    return RefreshService(
        uow=uow,
        jwt_provider=jwt_provider,
        token_hasher=token_hasher,
        settings=settings,
    )
