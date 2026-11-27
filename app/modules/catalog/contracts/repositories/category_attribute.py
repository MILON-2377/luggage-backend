import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.catalog.models.category_attribute import CategoryAttribute


class AbstractCategoryAttributeRepository(AbstractRepository):
    @abstractmethod
    def create(self, category_attribute: CategoryAttribute) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> list[CategoryAttribute]:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> None:
        raise NotImplementedError
