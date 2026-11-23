from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.security.token_hasher import TokenHasher
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.contracts.services.complete_login import (
    AbstractCompleteLoginService,
)
from app.modules.authentication.contracts.services.recovery_code_login_verify import (
    AbstractRecoveryCodeLoginVerifyService,
)
from app.modules.authentication.dependencies.complete_login import (
    get_complete_login_service,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.recovery_code_login_verify import (
    RecoveryCodeLoginVerifyService,
)


def get_recovery_code_login_verify_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
    complete_login_service: Annotated[
        AbstractCompleteLoginService,
        Depends(get_complete_login_service),
    ],
) -> AbstractRecoveryCodeLoginVerifyService:
    token_hasher: TokenHasher = SHA256TokenHasher()

    return RecoveryCodeLoginVerifyService(
        uow=uow,
        token_hasher=token_hasher,
        complete_login_service=complete_login_service,
    )