import uuid

from sqlalchemy import delete, select

from app.core.database.repositories.base import BaseRepository
from app.modules.catalog.contracts.repositories.category_media import (
    AbstractCategoryMediaRepository,
)
from app.modules.catalog.models.category_media import CategoryMedia


class CategoryMediaRepository(
    BaseRepository[CategoryMedia],
    AbstractCategoryMediaRepository,
):
    def create(self, category_media: CategoryMedia) -> None:
        self.session.add(category_media)

    async def get_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> list[CategoryMedia]:
        statement = (
            select(CategoryMedia)
            .where(CategoryMedia.category_id == category_id)
            .order_by(CategoryMedia.display_order.asc())
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_by_category_id(
        self,
        category_id: uuid.UUID,
    ) -> None:
        statement = delete(CategoryMedia).where(
            CategoryMedia.category_id == category_id,
        )

        await self.session.execute(statement)
