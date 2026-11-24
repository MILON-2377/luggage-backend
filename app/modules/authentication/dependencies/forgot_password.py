from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.email.template_renderer import (
    AbstractEmailTemplateRenderer,
)
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.security.token_hasher import TokenHasher
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.sha256_token_hasher import SHA256TokenHasher
from app.modules.authentication.contracts.services.forgot_password import (
    AbstractForgotPasswordService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.forgot_password import (
    ForgotPasswordService,
)
from app.modules.notification.contracts.services.email_outbox import (
    AbstractEmailOutboxService,
)
from app.modules.notification.dependencies.email_outbox import (
    get_email_outbox_service,
)
from app.modules.notification.dependencies.email_renderer import (
    get_email_renderer,
)


def get_forgot_password_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
    email_outbox_service: Annotated[
        AbstractEmailOutboxService,
        Depends(get_email_outbox_service),
    ],
    email_renderer: Annotated[
        AbstractEmailTemplateRenderer,
        Depends(get_email_renderer),
    ],
) -> AbstractForgotPasswordService:
    token_hasher: TokenHasher = SHA256TokenHasher()
    id_generator: AbstractIDGenerator = UUIDGenerator()

    return ForgotPasswordService(
        uow=uow,
        token_hasher=token_hasher,
        id_generator=id_generator,
        email_outbox_service=email_outbox_service,
        email_renderer=email_renderer,
        settings=settings,
    )
