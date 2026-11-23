
from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.integrations.security.webauthn_provider import WebAuthnProvider
from app.modules.authentication.contracts.services.passkey_registration import (
    AbstractPasskeyRegistrationService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.passkey_registration import (
    PasskeyRegistrationService,
)


def get_passkey_registration_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractPasskeyRegistrationService:
    id_generator: AbstractIDGenerator = UUIDGenerator()
    token_hasher: TokenHasher = SHA256TokenHasher()
    passkey_provider: PasskeyProvider = WebAuthnProvider()

    return PasskeyRegistrationService(
        uow=uow,
        id_generator=id_generator,
        token_hasher=token_hasher,
        passkey_provider=passkey_provider,
    )
