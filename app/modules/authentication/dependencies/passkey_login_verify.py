from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.passkey_provider import PasskeyProvider
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.integrations.security.webauthn_provider import WebAuthnProvider
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.passkey_login_verify import (
    AbstractPasskeyLoginVerifyService,
)
from app.modules.authentication.dependencies.complete_login import (
    get_complete_login_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.passkey_login_verify import (
    PasskeyLoginVerifyService,
)


def get_passkey_login_verify_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
    complete_login_service: Annotated[
        AbstractCompleteLoginService,
        Depends(get_complete_login_service),
    ],
) -> AbstractPasskeyLoginVerifyService:
    token_hasher: TokenHasher = SHA256TokenHasher()
    passkey_provider: PasskeyProvider = WebAuthnProvider()

    return PasskeyLoginVerifyService(
        uow=uow,
        token_hasher=token_hasher,
        passkey_provider=passkey_provider,
        complete_login_service=complete_login_service,
    )