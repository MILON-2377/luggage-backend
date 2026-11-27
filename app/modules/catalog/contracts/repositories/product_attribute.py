import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.catalog.models.product_attribute import ProductAttribute


class AbstractProductAttributeRepository(AbstractRepository):
    @abstractmethod
    async def get_by_id(
        self,
        attribute_id: uuid.UUID,
    ) -> ProductAttribute | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_ids(
        self,
        attribute_ids: list[uuid.UUID],
    ) -> list[ProductAttribute]:
        raise NotImplementedError