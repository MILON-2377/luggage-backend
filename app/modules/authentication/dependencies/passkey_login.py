
from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.integrations.security.webauthn_provider import WebAuthnProvider
from app.modules.authentication.contracts.services.passkey_login import (
    AbstractPasskeyLoginOptionsService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.passkey_login import (
    PasskeyLoginOptionsService,
)


def get_passkey_login_options_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractPasskeyLoginOptionsService:
    token_hasher: TokenHasher = SHA256TokenHasher()
    passkey_provider: PasskeyProvider = WebAuthnProvider()

    return PasskeyLoginOptionsService(
        uow=uow,
        token_hasher=token_hasher,
        passkey_provider=passkey_provider,
    )
