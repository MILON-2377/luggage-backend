import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.database.repositories.base import BaseRepository
from app.modules.catalog.contracts.repositories.product_category import (
    AbstractProductCategoryRepository,
)
from app.modules.catalog.enums import ProductCategoryStatus
from app.modules.catalog.models.category_attribute import CategoryAttribute
from app.modules.catalog.models.category_media import CategoryMedia
from app.modules.catalog.models.product_category import ProductCategory
from app.modules.media.models.media_asset import MediaAsset
from app.modules.media.models.media_file import MediaFile


def _media_load_options():
    return (
        selectinload(ProductCategory.category_media)
        .joinedload(CategoryMedia.media_asset)
        .selectinload(MediaAsset.files)
        .selectinload(MediaFile.storage_locations),
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ProductCategoryRepository(
    BaseRepository[ProductCategory],
    AbstractProductCategoryRepository,
):
    def create(self, category: ProductCategory) -> None:
        self.session.add(category)

    async def get_by_id(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategory | None:
        statement = select(ProductCategory).where(
            ProductCategory.id == category_id,
            ProductCategory.deleted_at.is_(None),
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_parent_and_slug(
        self,
        parent_id: uuid.UUID | None,
        slug: str,
    ) -> ProductCategory | None:
        parent_condition = (
            ProductCategory.parent_id.is_(None)
            if parent_id is None
            else ProductCategory.parent_id == parent_id
        )

        statement = (
            select(ProductCategory)
            .where(
                parent_condition,
                ProductCategory.slug == slug,
                ProductCategory.deleted_at.is_(None),
            )
            .limit(1)
        )

        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_root_page(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[ProductCategory], int]:
        root_conditions = (
            ProductCategory.parent_id.is_(None),
            ProductCategory.deleted_at.is_(None),
        )

        count_statement = (
            select(func.count()).select_from(ProductCategory).where(*root_conditions)
        )

        total_result = await self.session.execute(count_statement)
        total_items = total_result.scalar_one()

        if total_items == 0 or offset >= total_items:
            return [], total_items

        statement = (
            select(ProductCategory)
            .where(*root_conditions)
            .options(*_media_load_options())
            .order_by(
                ProductCategory.display_order,
                ProductCategory.name,
                ProductCategory.id,
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all()), total_items

    async def get_category_tree(
        self,
        root_ids: tuple[uuid.UUID, ...],
    ) -> list[ProductCategory]:
        if not root_ids:
            return []

        category_tree = (
            select(ProductCategory.id.label("id"))
            .where(
                ProductCategory.id.in_(root_ids),
                ProductCategory.deleted_at.is_(None),
            )
            .cte("category_tree", recursive=True)
        )

        descendants = (
            select(ProductCategory.id.label("id"))
            .join(
                category_tree,
                ProductCategory.parent_id == category_tree.c.id,
            )
            .where(ProductCategory.deleted_at.is_(None))
        )

        category_tree = category_tree.union(descendants)

        statement = (
            select(ProductCategory)
            .where(
                ProductCategory.id.in_(select(category_tree.c.id)),
                ProductCategory.deleted_at.is_(None),
            )
            .options(*_media_load_options())
            .order_by(
                ProductCategory.display_order,
                ProductCategory.name,
                ProductCategory.id,
            )
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def get_category_page(
        self,
        offset: int,
        limit: int,
        search: str | None = None,
        status: ProductCategoryStatus | None = None,
        parent_id: uuid.UUID | None = None,
        filter_by_parent: bool = False,
    ) -> tuple[list[ProductCategory], int]:
        filters = [
            ProductCategory.deleted_at.is_(None),
        ]

        normalized_search = search.strip() if search else ""
        if normalized_search:
            search_pattern = f"%{_escape_like(normalized_search)}%"
            filters.append(
                or_(
                    ProductCategory.name.ilike(search_pattern, escape="\\"),
                    ProductCategory.slug.ilike(search_pattern, escape="\\"),
                )
            )

        if status is not None:
            filters.append(ProductCategory.status == status)

        if filter_by_parent:
            filters.append(
                ProductCategory.parent_id.is_(None)
                if parent_id is None
                else ProductCategory.parent_id == parent_id
            )

        count_statement = (
            select(func.count()).select_from(ProductCategory).where(*filters)
        )

        total_result = await self.session.execute(count_statement)
        total_items = total_result.scalar_one()

        if total_items == 0 or offset >= total_items:
            return [], total_items

        statement = (
            select(ProductCategory)
            .where(*filters)
            .options(*_media_load_options())
            .order_by(
                ProductCategory.display_order,
                ProductCategory.name,
                ProductCategory.id,
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all()), total_items

    async def get_by_id_with_configuration(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategory | None:

        statement = (
            select(ProductCategory)
            .where(
                ProductCategory.id == category_id,
                ProductCategory.deleted_at.is_(None),
            )
            .options(
                selectinload(ProductCategory.parent),
                selectinload(ProductCategory.category_attributes).joinedload(
                    CategoryAttribute.attribute
                ),
                *_media_load_options(),
            )
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_parent_and_slug_excluding(
        self,
        parent_id: uuid.UUID | None,
        slug: str,
        exclude_category_id: uuid.UUID,
    ) -> ProductCategory | None:
        parent_condition = (
            ProductCategory.parent_id.is_(None)
            if parent_id is None
            else ProductCategory.parent_id == parent_id
        )

        statement = (
            select(ProductCategory)
            .where(
                parent_condition,
                ProductCategory.slug == slug,
                ProductCategory.id != exclude_category_id,
                ProductCategory.deleted_at.is_(None),
            )
            .limit(1)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def has_descendant(
        self,
        category_id: uuid.UUID,
        descendant_id: uuid.UUID,
    ) -> bool:
        descendants = (
            select(ProductCategory.id.label("id"))
            .where(
                ProductCategory.parent_id == category_id,
                ProductCategory.deleted_at.is_(None),
            )
            .cte("category_descendants", recursive=True)
        )

        descendants = descendants.union(
            select(ProductCategory.id.label("id"))
            .join(
                descendants,
                ProductCategory.parent_id == descendants.c.id,
            )
            .where(ProductCategory.deleted_at.is_(None))
        )

        statement = select(descendants.c.id).where(
            descendants.c.id == descendant_id,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none() is not None
