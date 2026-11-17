from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Self, TypeVar

from app.core.contracts.database.repository import AbstractRepository

RepositoryT = TypeVar("RepositoryT", bound=AbstractRepository)


class AbstractUnitOfWork(ABC):
    @abstractmethod
    def register_repository(
        self,
        repository_type: type[RepositoryT],
        repository: RepositoryT,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_repository(
        self,
        repository_type: type[RepositoryT],
    ) -> RepositoryT:
        raise NotImplementedError

    @abstractmethod
    async def flush(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def refresh(self, entity: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError
