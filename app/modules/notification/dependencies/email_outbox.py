from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.generators.uuid_generator import UUIDGenerator
from app.integrations.security.fernet_secret_encryptor import FernetSecretEncryptor
from app.modules.notification.services.email_outbox import EmailOutboxService


def get_email_outbox_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
) -> EmailOutboxService:
    return EmailOutboxService(
        uow=uow,
        secret_encryptor=FernetSecretEncryptor(),
        id_generator=UUIDGenerator(),
        settings=settings,
    )