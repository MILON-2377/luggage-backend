import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.contracts.database.unit_of_work import AbstractUnitOfWork
from app.core.database.dependencies import get_uow
from app.core.pagination.params import PaginationParams
from app.core.pagination.schemas import PaginationMetadata
from app.modules.catalog.contracts.services.product_category import (
    AbstractProductCategoryService,
)
from app.modules.catalog.dependencies.product_category import (
    get_product_category_service,
)
from app.modules.catalog.dtos.product_category import (
    CreateCategoryAttributeCommand,
    CreateCategoryMediaCommand,
    CreateProductCategoryCommand,
    CreateProductCategoryResult,
    UpdateProductCategoryCommand,
)
from app.modules.catalog.enums import ProductCategoryStatus
from app.modules.catalog.schemas.product_category import (
    CreateProductCategoryRequest,
    ProductCategoryDetailResponse,
    ProductCategoryListResponse,
    ProductCategoryTreeItemResponse,
    UpdateProductCategoryRequest,
)

router = APIRouter()


@router.get(
    "/categories",
    response_model=ProductCategoryListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_product_categories(
    pagination: Annotated[PaginationParams, Depends()],
    service: Annotated[
        AbstractProductCategoryService,
        Depends(get_product_category_service),
    ],
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=150),
    ] = None,
    category_status: Annotated[
        ProductCategoryStatus | None,
        Query(alias="status"),
    ] = None,
    parent_id: uuid.UUID | None = None,
    view: Literal["tree", "flat"] = "tree",
) -> ProductCategoryListResponse:
    result = await service.list_categories(
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        status=category_status,
        parent_id=parent_id,
        view=view,
    )

    return ProductCategoryListResponse(
        items=[
            ProductCategoryTreeItemResponse(
                category_id=item.category_id,
                parent_id=item.parent_id,
                name=item.name,
                slug=item.slug,
                description=item.description,
                display_order=item.display_order,
                status=item.status,
                media=[
                    {
                        "media_asset_id": media.media_asset_id,
                        "media_role": media.media_role,
                        "display_order": media.display_order,
                        "url": media.url,
                    }
                    for media in item.media
                ],
                children=[
                    ProductCategoryTreeItemResponse.model_validate(child)
                    for child in item.children
                ],
            )
            for item in result.items
        ],
        pagination=PaginationMetadata(
            page=result.page,
            page_size=result.page_size,
            total_items=result.total_items,
            total_pages=result.total_pages,
            has_previous=result.has_previous,
            has_next=result.has_next,
        ),
    )


@router.get(
    "/categories/{category_id}",
    response_model=ProductCategoryDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_product_category(
    category_id: uuid.UUID,
    service: Annotated[
        AbstractProductCategoryService,
        Depends(get_product_category_service),
    ],
) -> ProductCategoryDetailResponse:
    result = await service.get_category_configuration(category_id)

    return ProductCategoryDetailResponse.model_validate(result)


@router.post(
    "/categories",
    response_model=CreateProductCategoryResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_category(
    payload: CreateProductCategoryRequest,
    service: Annotated[
        AbstractProductCategoryService,
        Depends(get_product_category_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_uow),
    ],
) -> CreateProductCategoryResult:
    command = CreateProductCategoryCommand(
        parent_id=payload.parent_id,
        name=payload.name,
        description=payload.description,
        display_order=payload.display_order,
        attributes=tuple(
            CreateCategoryAttributeCommand(
                attribute_id=item.attribute_id,
                is_required=item.is_required,
                display_order=item.display_order,
            )
            for item in payload.attributes
        ),
        media=tuple(
            CreateCategoryMediaCommand(
                media_asset_id=item.media_asset_id,
                media_role=item.media_role,
                display_order=item.display_order,
            )
            for item in payload.media
        ),
    )

    result = await service.create(command)

    await uow.commit()

    return CreateProductCategoryResult(
        category_id=result.category_id,
        name=result.name,
        slug=result.slug,
        status=result.status,
    )


@router.patch(
    "/categories/{category_id}",
    response_model=ProductCategoryDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_product_category(
    category_id: uuid.UUID,
    payload: UpdateProductCategoryRequest,
    service: Annotated[
        AbstractProductCategoryService,
        Depends(get_product_category_service),
    ],
    uow: Annotated[
        AbstractUnitOfWork,
        Depends(get_uow),
    ],
) -> ProductCategoryDetailResponse:
    provided_fields = frozenset(payload.model_fields_set)

    command = UpdateProductCategoryCommand(
        category_id=category_id,
        parent_id=payload.parent_id,
        name=payload.name,
        status=payload.status,
        description=payload.description,
        display_order=payload.display_order,
        attributes=(
            tuple(
                CreateCategoryAttributeCommand(
                    attribute_id=item.attribute_id,
                    is_required=item.is_required,
                    display_order=item.display_order,
                )
                for item in payload.attributes
            )
            if "attributes" in provided_fields
            else None
        ),
        media=(
            tuple(
                CreateCategoryMediaCommand(
                    media_asset_id=item.media_asset_id,
                    media_role=item.media_role,
                    display_order=item.display_order,
                )
                for item in payload.media
            )
            if "media" in provided_fields
            else None
        ),
        provided_fields=provided_fields,
    )

    result = await service.update_category(command)

    await uow.commit()

    return ProductCategoryDetailResponse.model_validate(result)
