import asyncio
import logging
from types import TracebackType
from typing import Any, Self, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts.database.repository import AbstractRepository
from app.core.contracts.database.unit_of_work import AbstractUnitOfWork, RepositoryT

logger = logging.getLogger(__name__)


class UnitOfWork(AbstractUnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._entered = False
        self._repositories: dict[type[AbstractRepository], AbstractRepository] = {}

    def register_repository(
        self,
        repository_type: type[RepositoryT],
        repository: RepositoryT,
    ) -> None:
        if not isinstance(repository_type, type) or not issubclass(
            repository_type, AbstractRepository
        ):
            raise TypeError(
                f"{getattr(repository_type, '__name__', repository_type)} "
                "must be a subclass of AbstractRepository"
            )

        if not isinstance(repository, repository_type):
            raise TypeError(
                f"Repository must be an instance of {repository_type.__name__}"
            )

        if repository_type in self._repositories:
            raise ValueError(f"{repository_type.__name__} is already registered")

        if getattr(repository, "session", None) is not self.session:
            raise ValueError("All repositories must use the UnitOfWork session")

        self._repositories[repository_type] = repository

    def has_repository(self, repository_type: type[AbstractRepository]) -> bool:
        return repository_type in self._repositories

    def get_repository(
        self,
        repository_type: type[RepositoryT],
    ) -> RepositoryT:
        try:
            repository = self._repositories[repository_type]
        except KeyError:
            raise LookupError(f"{repository_type.__name__} is not registered") from None

        return cast(RepositoryT, repository)

    async def flush(self) -> None:
        self._require_entered()
        await self.session.flush()

    async def refresh(self, entity: Any) -> None:
        self._require_entered()
        await self.session.refresh(entity)

    async def commit(self) -> None:
        self._require_entered()
        await self.session.commit()

    async def rollback(self) -> None:
        self._require_entered()
        await self.session.rollback()

    async def __aenter__(self) -> Self:
        if self._entered:
            raise RuntimeError("UnitOfWork is not re-entrant")

        try:
            if not self.session.in_transaction():
                await self.session.begin()
        except BaseException:
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
        except Exception:
            if exc_type is None:
                raise
            logger.exception("UnitOfWork cleanup failed while handling %r", exc)
        finally:
            self._entered = False

    async def _cleanup(self) -> None:
        try:
            if self.session.in_transaction():
                await self.session.rollback()
        finally:
            await self.session.close()

    def _require_entered(self) -> None:
        if not self._entered:
            raise RuntimeError("UnitOfWork must be used inside 'async with'")
