from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.contracts.services.initial_mfa_setup_resend import (
    AbstractInitialMFASetupResendService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.initial_mfa_setup_resend import (
    InitialMFASetupResendService,
)
from app.modules.notification.dependencies.email_outbox import (
    get_email_outbox_service,
)
from app.modules.notification.dependencies.email_renderer import (
    get_email_renderer,
)
from app.modules.notification.repositories.registry import (
    register_notification_repositories,
)


def get_initial_mfa_setup_resend_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractInitialMFASetupResendService:
    register_notification_repositories(uow)

    id_generator: AbstractIDGenerator = UUIDGenerator()
    token_hasher: TokenHasher = SHA256TokenHasher()

    return InitialMFASetupResendService(
        uow=uow,
        id_generator=id_generator,
        token_hasher=token_hasher,
        email_outbox_service=get_email_outbox_service(uow),
        email_renderer=get_email_renderer(),
        settings=settings,
    )
