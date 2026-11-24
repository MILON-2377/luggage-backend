from typing import Annotated

from fastapi import Depends

from app.core.database.dependencies import get_uow
from app.core.database.unit_of_work import UnitOfWork
from app.modules.notification.repositories.registry import (
    register_notification_repositories,
)


def get_notification_uow(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UnitOfWork:
    register_notification_repositories(uow)
    return uow