from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.argon2_password_hasher import (
    Argon2PasswordHasher,
    PasswordHasher,
)
from app.integrations.security.sha256_token_hasher import (
    SHA256TokenHasher,
    TokenHasher,
)
from app.modules.authentication.contracts.services.login import (
    AbstractLoginService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.login import LoginService


def get_login_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractLoginService:
    id_generator: AbstractIDGenerator = UUIDGenerator()
    password_hasher: PasswordHasher = Argon2PasswordHasher()
    token_hasher: TokenHasher = SHA256TokenHasher()

    return LoginService(
        uow=uow,
        id_generator=id_generator,
        password_hasher=password_hasher,
        token_hasher=token_hasher,
        settings=settings,
    )