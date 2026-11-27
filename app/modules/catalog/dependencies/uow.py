from typing import Annotated

from fastapi import Depends

from app.core.database.dependencies import get_uow
from app.core.database.unit_of_work import UnitOfWork
from app.modules.catalog.repositories.registry import (
    register_catalog_repositories,
)


def get_catalog_uow(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UnitOfWork:
    register_catalog_repositories(uow)
    return uow
