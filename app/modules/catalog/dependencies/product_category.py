from typing import Annotated

from fastapi import Depends

from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.generators.slug_generator import AbstractSlugGenerator
from app.core.database.unit_of_work import UnitOfWork
from app.core.generators.dependencies import IDGeneratorDep, SlugGeneratorDep
from app.modules.catalog.dependencies.uow import get_catalog_uow
from app.modules.catalog.services.product_category import ProductCategoryService


def get_product_category_service(
    uow: Annotated[UnitOfWork, Depends(get_catalog_uow)],
    id_generator: IDGeneratorDep,
    slug_generator: SlugGeneratorDep,
) -> ProductCategoryService:
    return ProductCategoryService(
        uow=uow,
        id_generator=id_generator,
        slug_generator=slug_generator,
    )


ProductCategoryServiceDep = Annotated[
    ProductCategoryService,
    Depends(get_product_category_service),
]