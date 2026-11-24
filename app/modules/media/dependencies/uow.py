from typing import Annotated

from fastapi import Depends

from app.core.database.dependencies import get_uow
from app.core.database.unit_of_work import UnitOfWork
from app.modules.media.repositories.registry import register_media_repositories


def get_media_uow(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UnitOfWork:
    register_media_repositories(uow)
    return uow