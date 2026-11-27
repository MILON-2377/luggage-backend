import uuid

from sqlalchemy import select

from app.core.database.repositories.base import BaseRepository
from app.modules.catalog.contracts.repositories.product_attribute import (
    AbstractProductAttributeRepository,
)
from app.modules.catalog.models.product_attribute import ProductAttribute


class ProductAttributeRepository(
    BaseRepository[ProductAttribute],
    AbstractProductAttributeRepository,
):
    async def get_by_id(
        self,
        attribute_id: uuid.UUID,
    ) -> ProductAttribute | None:
        statement = select(ProductAttribute).where(
            ProductAttribute.id == attribute_id,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        attribute_ids: list[uuid.UUID],
    ) -> list[ProductAttribute]:
        if not attribute_ids:
            return []

        statement = select(ProductAttribute).where(
            ProductAttribute.id.in_(attribute_ids),
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())