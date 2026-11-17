from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from app.core.database.session import AsyncSessionLocal
from app.core.database.unit_of_work import UnitOfWork


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    async with AsyncSessionLocal() as session, UnitOfWork(session) as uow:
        yield uow


CoreUoW = Annotated[UnitOfWork, Depends(get_uow)]
