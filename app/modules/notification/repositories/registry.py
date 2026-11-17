from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.notification.contracts.repositories.email_outbox import (
    AbstractEmailOutboxRepository,
)
from app.modules.notification.repositories import EmailOutboxRepository


def register_notification_repositories(uow: AbstractUnitOfWork) -> None:
    session = uow.session

    repositories = (AbstractEmailOutboxRepository, EmailOutboxRepository)

    for contract, implementation in repositories:
        uow.register_repository(contract, implementation(session))
