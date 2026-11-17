from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.contracts.database.repository import AbstractRepository

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class BaseRepository(AbstractRepository, Generic[ModelT]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def create(self, entity: ModelT) -> None:
        self.session.add(entity)
