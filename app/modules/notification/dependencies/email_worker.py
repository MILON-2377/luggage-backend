from httpx import AsyncClient

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.email.brevo import (
    BrevoEmailProvider,
)
from app.integrations.security.fernet_secret_encryptor import (
    FernetSecretEncryptor,
)
from app.modules.notification.services.email_outbox import EmailOutboxService


def get_email_delivery_service(
    uow: AbstractUnitOfWork,
    http_client: AsyncClient,
) -> EmailOutboxService:
    return EmailOutboxService(
        uow=uow,
        secret_encryptor=FernetSecretEncryptor(),
        id_generator=UUIDGenerator(),
        settings=settings,
        email_provider=BrevoEmailProvider(
            settings=settings,
            client=http_client,
        ),
    )
