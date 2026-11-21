from typing import Annotated

from fastapi import Depends

from app.core.database.dependencies import get_uow
from app.core.database.unit_of_work import UnitOfWork
from app.modules.authentication.repositories.registry import (
    register_authentication_repositories,
)


def get_auth_uow(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UnitOfWork:
    register_authentication_repositories(uow)
    return uow