import uuid
from math import ceil
from typing import Literal

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.contracts.generators.slug_generator import AbstractSlugGenerator
from app.modules.catalog.contracts.repositories.category_attribute import (
    AbstractCategoryAttributeRepository,
)
from app.modules.catalog.contracts.repositories.category_media import (
    AbstractCategoryMediaRepository,
)
from app.modules.catalog.contracts.repositories.product_attribute import (
    AbstractProductAttributeRepository,
)
from app.modules.catalog.contracts.repositories.product_category import (
    AbstractProductCategoryRepository,
)
from app.modules.catalog.contracts.services.product_category import (
    AbstractProductCategoryService,
)
from app.modules.catalog.dtos.product_category import (
    CreateProductCategoryCommand,
    CreateProductCategoryResult,
    ProductCategoryDetailResult,
    ProductCategoryListResult,
    ProductCategoryMediaItem,
    ProductCategoryTreeItem,
    UpdateProductCategoryCommand,
)
from app.modules.catalog.enums import ProductCategoryStatus
from app.modules.catalog.errors.product_category import (
    ProductCategoryAttributeNotFoundError,
    ProductCategoryDuplicateAttributeError,
    ProductCategoryDuplicateMediaError,
    ProductCategoryInvalidParentError,
    ProductCategoryMediaNotFoundError,
    ProductCategoryMediaNotReadyError,
    ProductCategoryNotFoundError,
    ProductCategoryParentNotFoundError,
    ProductCategorySlugConflictError,
)
from app.modules.catalog.models.category_attribute import CategoryAttribute
from app.modules.catalog.models.category_media import CategoryMedia
from app.modules.catalog.models.product_category import ProductCategory
from app.modules.media.contracts.repositories.media_asset import (
    AbstractMediaAssetRepository,
)
from app.modules.media.enums import (
    MediaFileRole,
    MediaStatus,
    StorageLocationStatus,
)


class ProductCategoryService(AbstractProductCategoryService):
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        id_generator: AbstractIDGenerator,
        slug_generator: AbstractSlugGenerator,
    ) -> None:
        self.uow = uow
        self.id_generator = id_generator
        self.slug_generator = slug_generator

    async def create(
        self,
        command: CreateProductCategoryCommand,
    ) -> CreateProductCategoryResult:
        category_repository = self.uow.get_repository(
            AbstractProductCategoryRepository,
        )
        attribute_repository = self.uow.get_repository(
            AbstractProductAttributeRepository,
        )
        category_attribute_repository = self.uow.get_repository(
            AbstractCategoryAttributeRepository,
        )
        category_media_repository = self.uow.get_repository(
            AbstractCategoryMediaRepository,
        )
        media_asset_repository = self.uow.get_repository(
            AbstractMediaAssetRepository,
        )

        if command.parent_id is not None:
            if await category_repository.get_by_id(command.parent_id) is None:
                raise ProductCategoryParentNotFoundError(str(command.parent_id))

        slug = self.slug_generator.generate(command.name)

        existing_category = await category_repository.get_by_parent_and_slug(
            parent_id=command.parent_id,
            slug=slug,
        )
        if existing_category is not None:
            raise ProductCategorySlugConflictError()

        attribute_ids = [item.attribute_id for item in command.attributes]
        if len(attribute_ids) != len(set(attribute_ids)):
            raise ProductCategoryDuplicateAttributeError()

        if attribute_ids:
            attributes = await attribute_repository.get_by_ids(attribute_ids)
            found_attribute_ids = {attribute.id for attribute in attributes}

            for attribute_id in attribute_ids:
                if attribute_id not in found_attribute_ids:
                    raise ProductCategoryAttributeNotFoundError(str(attribute_id))

        media_keys = [(item.media_asset_id, item.media_role) for item in command.media]
        if len(media_keys) != len(set(media_keys)):
            raise ProductCategoryDuplicateMediaError()

        media_asset_ids = list(
            dict.fromkeys(item.media_asset_id for item in command.media)
        )

        if media_asset_ids:
            media_assets = await media_asset_repository.get_by_ids(media_asset_ids)
            media_assets_by_id = {asset.id: asset for asset in media_assets}

            for media_asset_id in media_asset_ids:
                media_asset = media_assets_by_id.get(media_asset_id)

                if media_asset is None:
                    raise ProductCategoryMediaNotFoundError(str(media_asset_id))

                if media_asset.status != MediaStatus.READY:
                    raise ProductCategoryMediaNotReadyError(str(media_asset_id))

        category = ProductCategory(
            id=self.id_generator.generate(),
            parent_id=command.parent_id,
            name=command.name,
            slug=slug,
            description=command.description,
            display_order=command.display_order,
        )
        category_repository.create(category)

        await self.uow.flush()

        for item in command.attributes:
            category_attribute_repository.create(
                CategoryAttribute(
                    id=self.id_generator.generate(),
                    category_id=category.id,
                    attribute_id=item.attribute_id,
                    is_required=item.is_required,
                    display_order=item.display_order,
                ),
            )

        for item in command.media:
            category_media_repository.create(
                CategoryMedia(
                    id=self.id_generator.generate(),
                    category_id=category.id,
                    media_asset_id=item.media_asset_id,
                    media_role=item.media_role,
                    display_order=item.display_order,
                ),
            )

        await self.uow.flush()

        return CreateProductCategoryResult(
            category_id=category.id,
            name=category.name,
            slug=category.slug,
            status=category.status.value,
        )

    async def list_categories(
        self,
        page: int,
        page_size: int,
        search: str | None = None,
        status: ProductCategoryStatus | None = None,
        parent_id: uuid.UUID | None = None,
        only_roots: bool = False,
        view: Literal["tree", "flat"] = "tree",
    ) -> ProductCategoryListResult:
        repository = self.uow.get_repository(
            AbstractProductCategoryRepository,
        )

        offset = (page - 1) * page_size
        normalized_search = search.strip() if search else None
        has_filters = bool(
            normalized_search
            or status is not None
            or parent_id is not None
            or only_roots
        )

        if view == "flat" or has_filters:
            categories, total_items = await repository.get_category_page(
                offset=offset,
                limit=page_size,
                search=normalized_search,
                status=status,
                parent_id=parent_id,
                filter_by_parent=parent_id is not None or only_roots,
            )

            items = tuple(
                self._build_item(category, children=()) for category in categories
            )
        else:
            roots, total_items = await repository.get_root_page(
                offset=offset,
                limit=page_size,
            )

            if roots:
                categories = await repository.get_category_tree(
                    tuple(category.id for category in roots),
                )
            else:
                categories = []

            children_by_parent: dict[uuid.UUID, list[ProductCategory]] = {}
            for category in categories:
                if category.parent_id is not None:
                    children_by_parent.setdefault(category.parent_id, []).append(
                        category
                    )

            def build_tree(
                category: ProductCategory,
                visited: frozenset[uuid.UUID],
            ) -> ProductCategoryTreeItem:
                path = visited | {category.id}
                children = tuple(
                    build_tree(child, path)
                    for child in children_by_parent.get(category.id, [])
                    if child.id not in path
                )
                return self._build_item(category, children=children)

            items = tuple(build_tree(root, frozenset()) for root in roots)

        total_pages = ceil(total_items / page_size) if total_items else 0

        return ProductCategoryListResult(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )

    async def get_category_configuration(
        self,
        category_id: uuid.UUID,
    ) -> ProductCategoryDetailResult:
        from app.modules.catalog.dtos.product_category import (
            ProductCategoryAttributeItem,
            ProductCategoryDetailResult,
        )
        from app.modules.catalog.errors.product_category import (
            ProductCategoryNotFoundError,
        )

        repository = self.uow.get_repository(
            AbstractProductCategoryRepository,
        )

        category = await repository.get_by_id_with_configuration(category_id)

        if category is None:
            raise ProductCategoryNotFoundError()

        attributes = tuple(
            ProductCategoryAttributeItem(
                attribute_id=item.attribute_id,
                name=item.attribute.name,
                slug=item.attribute.slug,
                description=item.attribute.description,
                data_type=item.attribute.data_type.value,
                unit=item.attribute.unit,
                is_custom_allowed=item.attribute.is_custom_allowed,
                is_required=item.is_required,
                display_order=item.display_order,
            )
            for item in sorted(
                category.category_attributes,
                key=lambda item: (item.display_order, str(item.attribute_id)),
            )
        )

        return ProductCategoryDetailResult(
            category_id=category.id,
            parent_id=category.parent_id,
            parent_name=category.parent.name if category.parent else None,
            name=category.name,
            slug=category.slug,
            description=category.description,
            display_order=category.display_order,
            status=category.status.value,
            attributes=attributes,
            media=self._build_media(category),
        )

    async def update_category(
        self,
        command: UpdateProductCategoryCommand,
    ) -> ProductCategoryDetailResult:

        category_repository = self.uow.get_repository(
            AbstractProductCategoryRepository,
        )
        attribute_repository = self.uow.get_repository(
            AbstractProductAttributeRepository,
        )
        category_attribute_repository = self.uow.get_repository(
            AbstractCategoryAttributeRepository,
        )
        category_media_repository = self.uow.get_repository(
            AbstractCategoryMediaRepository,
        )
        media_asset_repository = self.uow.get_repository(
            AbstractMediaAssetRepository,
        )

        category = await category_repository.get_by_id(command.category_id)
        if category is None:
            raise ProductCategoryNotFoundError()

        parent_id = category.parent_id
        if "parent_id" in command.provided_fields:
            parent_id = command.parent_id

            if parent_id is not None:
                if await category_repository.get_by_id(parent_id) is None:
                    raise ProductCategoryParentNotFoundError(str(parent_id))

                if parent_id == category.id or await category_repository.has_descendant(
                    category_id=category.id,
                    descendant_id=parent_id,
                ):
                    raise ProductCategoryInvalidParentError()

        name = category.name
        slug = category.slug

        if "name" in command.provided_fields:
            name = command.name
            slug = self.slug_generator.generate(name)

        if parent_id != category.parent_id or slug != category.slug:
            existing_category = (
                await category_repository.get_by_parent_and_slug_excluding(
                    parent_id=parent_id,
                    slug=slug,
                    exclude_category_id=category.id,
                )
            )
            if existing_category is not None:
                raise ProductCategorySlugConflictError()

        if "attributes" in command.provided_fields:
            attribute_ids = [item.attribute_id for item in command.attributes]

            if len(attribute_ids) != len(set(attribute_ids)):
                raise ProductCategoryDuplicateAttributeError()

            if attribute_ids:
                attributes = await attribute_repository.get_by_ids(
                    attribute_ids,
                )
                found_attribute_ids = {attribute.id for attribute in attributes}

                for attribute_id in attribute_ids:
                    if attribute_id not in found_attribute_ids:
                        raise ProductCategoryAttributeNotFoundError(
                            str(attribute_id),
                        )

        if "media" in command.provided_fields:
            media_keys = [
                (item.media_asset_id, item.media_role) for item in command.media
            ]

            if len(media_keys) != len(set(media_keys)):
                raise ProductCategoryDuplicateMediaError()

            media_asset_ids = list(
                dict.fromkeys(item.media_asset_id for item in command.media)
            )

            if media_asset_ids:
                media_assets = await media_asset_repository.get_by_ids(
                    media_asset_ids,
                )
                media_assets_by_id = {asset.id: asset for asset in media_assets}

                for media_asset_id in media_asset_ids:
                    media_asset = media_assets_by_id.get(media_asset_id)

                    if media_asset is None:
                        raise ProductCategoryMediaNotFoundError(
                            str(media_asset_id),
                        )

                    if media_asset.status != MediaStatus.READY:
                        raise ProductCategoryMediaNotReadyError(
                            str(media_asset_id),
                        )

        category.parent_id = parent_id
        category.name = name
        category.slug = slug

        if "status" in command.provided_fields:
            category.status = command.status

        if "description" in command.provided_fields:
            category.description = command.description

        if "display_order" in command.provided_fields:
            category.display_order = command.display_order

        if "attributes" in command.provided_fields:
            await category_attribute_repository.delete_by_category_id(
                category.id,
            )

            for item in command.attributes:
                category_attribute_repository.create(
                    CategoryAttribute(
                        id=self.id_generator.generate(),
                        category_id=category.id,
                        attribute_id=item.attribute_id,
                        is_required=item.is_required,
                        display_order=item.display_order,
                    ),
                )

        if "media" in command.provided_fields:
            await category_media_repository.delete_by_category_id(
                category.id,
            )

            for item in command.media:
                category_media_repository.create(
                    CategoryMedia(
                        id=self.id_generator.generate(),
                        category_id=category.id,
                        media_asset_id=item.media_asset_id,
                        media_role=item.media_role,
                        display_order=item.display_order,
                    ),
                )

        await self.uow.flush()

        return await self.get_category_configuration(category.id)

    def _build_item(
        self,
        category: ProductCategory,
        children: tuple[ProductCategoryTreeItem, ...],
    ) -> ProductCategoryTreeItem:
        return ProductCategoryTreeItem(
            category_id=category.id,
            parent_id=category.parent_id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            display_order=category.display_order,
            status=category.status.value,
            media=self._build_media(category),
            children=children,
        )

    @staticmethod
    def _build_media(
        category: ProductCategory,
    ) -> tuple[ProductCategoryMediaItem, ...]:
        media_items: list[ProductCategoryMediaItem] = []

        for category_media in category.category_media:
            asset = category_media.media_asset

            if asset.status != MediaStatus.READY:
                continue

            original_file = next(
                (
                    media_file
                    for media_file in asset.files
                    if media_file.file_role == MediaFileRole.ORIGINAL
                ),
                None,
            )

            if original_file is None:
                continue

            primary_location = next(
                (
                    location
                    for location in original_file.storage_locations
                    if location.is_primary
                    and location.status == StorageLocationStatus.READY
                    and location.storage_url
                ),
                None,
            )

            if primary_location is None:
                continue

            media_items.append(
                ProductCategoryMediaItem(
                    media_asset_id=asset.id,
                    media_role=category_media.media_role,
                    display_order=category_media.display_order,
                    url=primary_location.storage_url,
                ),
            )

        return tuple(
            sorted(
                media_items,
                key=lambda item: (
                    item.display_order,
                    str(item.media_asset_id),
                    item.media_role.value,
                ),
            )
        )
