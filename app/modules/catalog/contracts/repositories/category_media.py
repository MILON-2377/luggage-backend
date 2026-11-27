import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.catalog.models.category_media import CategoryMedia


class AbstractCategoryMediaRepository(AbstractRepository):
    @abstractmethod
    def create(self, category_media: CategoryMedia) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> list[CategoryMedia]:
        raise NotImplementedError


    @abstractmethod
    async def delete_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> None:
        raise NotImplementedError
