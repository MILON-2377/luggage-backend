from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.sha256_token_hasher import (
    SHA256TokenHasher,
    TokenHasher,
)
from app.modules.authentication.contracts.services.verify_password_reset import (
    AbstractVerifyPasswordResetService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.verify_password_reset import (
    VerifyPasswordResetService,
)


def get_verify_password_reset_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractVerifyPasswordResetService:
    id_generator: AbstractIDGenerator = UUIDGenerator()
    token_hasher: TokenHasher = SHA256TokenHasher()

    return VerifyPasswordResetService(
        uow=uow,
        id_generator=id_generator,
        token_hasher=token_hasher,
        settings=settings,
    )