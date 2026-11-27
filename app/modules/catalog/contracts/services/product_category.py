import uuid
from abc import abstractmethod
from typing import Literal

from app.core.contracts.services.service import AbstractService
from app.modules.catalog.dtos.product_category import (
    CreateProductCategoryCommand,
    CreateProductCategoryResult,
    ProductCategoryDetailResult,
    ProductCategoryListResult,
    UpdateProductCategoryCommand,
)
from app.modules.catalog.enums import ProductCategoryStatus


class AbstractProductCategoryService(AbstractService):
    @abstractmethod
    async def create(
        self,
        command: CreateProductCategoryCommand,
    ) -> CreateProductCategoryResult:
        raise NotImplementedError

    @abstractmethod
    async def list_categories(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        status: ProductCategoryStatus | None = None,
        parent_id: uuid.UUID | None = None,
        view: Literal["tree", "flat"] = "tree",
    ) -> ProductCategoryListResult:
        raise NotImplementedError

    @abstractmethod
    async def get_category_configuration(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategoryDetailResult:
        raise NotImplementedError

    @abstractmethod
    async def update_category(
        self,
        command: UpdateProductCategoryCommand,
    ) -> ProductCategoryDetailResult:
        raise NotImplementedError
