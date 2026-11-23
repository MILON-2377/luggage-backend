from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.secret_encryptor import SecretEncryptor
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.contracts.security.totp_provider import TOTPProvider
from app.integrations.security.fernet_secret_encryptor import FernetSecretEncryptor
from app.integrations.security.pyotp_provider import PyOTPProvider
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.totp_login_verify import (
    AbstractTotpLoginVerifyService,
)
from app.modules.authentication.dependencies.complete_login import (
    get_complete_login_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.totp_login_verify import (
    TotpLoginVerifyService,
)


def get_totp_login_verify_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
    complete_login_service: Annotated[
        AbstractCompleteLoginService,
        Depends(get_complete_login_service),
    ],
) -> AbstractTotpLoginVerifyService:
    token_hasher: TokenHasher = SHA256TokenHasher()
    totp_provider: TOTPProvider = PyOTPProvider()
    secret_encryptor: SecretEncryptor = FernetSecretEncryptor()

    return TotpLoginVerifyService(
        uow=uow,
        token_hasher=token_hasher,
        totp_provider=totp_provider,
        secret_encryptor=secret_encryptor,
        complete_login_service=complete_login_service,
    )