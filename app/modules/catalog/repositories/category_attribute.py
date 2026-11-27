import uuid

from sqlalchemy import delete, select

from app.core.database.repositories.base import BaseRepository
from app.modules.catalog.contracts.repositories.category_attribute import (
    AbstractCategoryAttributeRepository,
)
from app.modules.catalog.models.category_attribute import CategoryAttribute


class CategoryAttributeRepository(
    BaseRepository[CategoryAttribute],
    AbstractCategoryAttributeRepository,
):
    def create(self, category_attribute: CategoryAttribute) -> None:
        self.session.add(category_attribute)

    async def get_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> list[CategoryAttribute]:
        statement = (
            select(CategoryAttribute)
            .where(CategoryAttribute.category_id == category_id)
            .order_by(CategoryAttribute.display_order.asc())
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> None:
        statement = delete(CategoryAttribute).where(
            CategoryAttribute.category_id == category_id,
        )

        await self.session.execute(statement)
