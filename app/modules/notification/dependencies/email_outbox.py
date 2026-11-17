from functools import lru_cache

from app.core.config import settings
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.email.brevo import BrevoEmailProvider
from app.integrations.security.fernet_secret_encryptor import (
    FernetSecretEncryptor,
)
from app.modules.notification.services.email_outbox import EmailOutboxService


@lru_cache
def get_email_provider() -> BrevoEmailProvider:
    return BrevoEmailProvider(settings)


@lru_cache
def get_secret_encryptor() -> FernetSecretEncryptor:
    return FernetSecretEncryptor()


@lru_cache
def get_id_generator() -> UUIDGenerator:
    return UUIDGenerator()


def get_email_outbox_service(uow) -> EmailOutboxService:
    return EmailOutboxService(
        uow=uow,
        email_provider=get_email_provider(),
        secret_encryptor=get_secret_encryptor(),
        id_generator=get_id_generator(),
        settings=settings,
    )
