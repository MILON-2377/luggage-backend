import uuid
from abc import abstractmethod

from app.core.contracts.database.repository import AbstractRepository
from app.modules.catalog.enums import ProductCategoryStatus
from app.modules.catalog.models.product_category import ProductCategory


class AbstractProductCategoryRepository(AbstractRepository):
    @abstractmethod
    async def get_by_id(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategory | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_parent_and_slug(
        self,
        parent_id: uuid.UUID | None,
        slug: str,
    ) -> ProductCategory | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, category: ProductCategory) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_root_page(
        self,
        offset: int,
        limit: int,
    ) -> tuple[list[ProductCategory], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_category_tree(
        self,
        root_ids: tuple[uuid.UUID, ...],
    ) -> list[ProductCategory]:
        raise NotImplementedError

    @abstractmethod
    async def get_category_page(
        self,
        offset: int,
        limit: int,
        search: str | None = None,
        status: ProductCategoryStatus | None = None,
        parent_id: uuid.UUID | None = None,
        filter_by_parent: bool = False,
    ) -> tuple[list[ProductCategory], int]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_with_configuration(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategory | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_parent_and_slug_excluding(
        self,
        parent_id: uuid.UUID | None,
        slug: str,
        exclude_category_id: uuid.UUID,
    ) -> ProductCategory | None:
        raise NotImplementedError


    @abstractmethod
    async def has_descendant(
        self,
        category_id: uuid.UUID,
        descendant_id: uuid.UUID,
    ) -> bool:
        raise NotImplementedError