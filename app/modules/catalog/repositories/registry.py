from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.modules.catalog.contracts.repositories import (
    AbstractCategoryAttributeRepository,
    AbstractCategoryMediaRepository,
    AbstractProductAttributeRepository,
    AbstractProductCategoryRepository,
)
from app.modules.catalog.repositories.category_attribute import (
    CategoryAttributeRepository,
)
from app.modules.catalog.repositories.category_media import (
    CategoryMediaRepository,
)
from app.modules.catalog.repositories.product_attribute import (
    ProductAttributeRepository,
)
from app.modules.catalog.repositories.product_category import (
    ProductCategoryRepository,
)
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.repositories.media_asset import MediaAssetRepository


def register_catalog_repositories(
    uow: AbstractUnitOfWork,
) -> None:
    session = uow.session

    repositories = (
        (AbstractProductCategoryRepository, ProductCategoryRepository),
        (AbstractCategoryAttributeRepository, CategoryAttributeRepository),
        (AbstractCategoryMediaRepository, CategoryMediaRepository),
        (AbstractProductAttributeRepository, ProductAttributeRepository),
        (AbstractMediaAssetRepository, MediaAssetRepository),
    )

    for contract, implementation in repositories:
        uow.register_repository(
            contract,
            implementation(session),
        )