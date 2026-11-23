from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.integrations.security.sha256_token_hasher import (
    SHA256TokenHasher,
    TokenHasher,
)
from app.modules.authentication.contracts.services.logout import (
    AbstractLogoutService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.logout import LogoutService


def get_logout_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractLogoutService:
    token_hasher: TokenHasher = SHA256TokenHasher()

    return LogoutService(
        uow=uow,
        token_hasher=token_hasher,
    )