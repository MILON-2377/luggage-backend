from typing import Annotated

from fastapi import Depends

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.authentication.contracts.services.session import (
    AbstractAdminSessionService,
)
from app.modules.authentication.dependencies.uow import get_auth_uow
from app.modules.authentication.services.session import AdminSessionService


def get_admin_session_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_auth_uow)],
) -> AbstractAdminSessionService:
    return AdminSessionService(uow=uow)