from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.fernet_secret_encryptor import (
    FernetSecretEncryptor,
)
from app.integrations.security.pyotp_provider import PyOTPProvider
from app.integrations.security.sha256_token_hasher import (
    SHA256TokenHasher,
    TokenHasher,
)
from app.modules.authentication.contracts.services.initial_totp_enrollment import (
    AbstractInitialTOTPEnrollmentService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.initial_totp_enrollment import (
    InitialTOTPEnrollmentService,
)


def get_initial_totp_enrollment_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractInitialTOTPEnrollmentService:
    id_generator: AbstractIDGenerator = UUIDGenerator()
    token_hasher: TokenHasher = SHA256TokenHasher()
    secret_encryptor = FernetSecretEncryptor()
    totp_provider = PyOTPProvider()

    return InitialTOTPEnrollmentService(
        uow=uow,
        id_generator=id_generator,
        token_hasher=token_hasher,
        secret_encryptor=secret_encryptor,
        totp_provider=totp_provider,
        settings=settings,
    )
