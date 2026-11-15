import asyncio
from types import TracebackType
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._entered = False

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, entity: Any) -> None:
        await self.session.refresh(entity)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def __aenter__(self) -> Self:
        if self._entered:
            raise RuntimeError("UnitOfWork is not re-entrant")

        try:
            if not self.session.in_transaction():
                await self.session.begin()
        except BaseException:
            # __aexit__ will not run if __aenter__ raises, so clean up here
            await asyncio.shield(self.session.close())
            raise

        self._entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await asyncio.shield(self._cleanup())
        finally:
            self._entered = False

    async def _cleanup(self) -> None:
        try:
            if self.session.in_transaction():
                await self.session.rollback()
        finally:
            await self.session.close()
