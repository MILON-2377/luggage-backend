import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination.schemas import PaginatedResponse
from app.modules.catalog.enums import CategoryMediaRole, ProductCategoryStatus


class CategoryAttributeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute_id: uuid.UUID
    is_required: bool = False
    display_order: int = Field(default=0, ge=0)


class CategoryMediaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_asset_id: uuid.UUID
    media_role: CategoryMediaRole
    display_order: int = Field(default=0, ge=0)


class CreateProductCategoryRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    parent_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    display_order: int = Field(default=0, ge=0)
    attributes: list[CategoryAttributeInput] = Field(default_factory=list)
    media: list[CategoryMediaInput] = Field(default_factory=list)


class ProductCategoryMediaResponse(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
    )

    media_asset_id: uuid.UUID
    media_role: CategoryMediaRole
    display_order: int
    url: str


class ProductCategoryTreeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    display_order: int
    status: str
    media: list[ProductCategoryMediaResponse] = Field(default_factory=list)
    children: list["ProductCategoryTreeItemResponse"] = Field(default_factory=list)


class ProductCategoryListResponse(PaginatedResponse[ProductCategoryTreeItemResponse]):
    pass


class ProductCategoryAttributeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    attribute_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    data_type: str
    unit: str | None
    is_custom_allowed: bool
    is_required: bool
    display_order: int


class ProductCategoryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: uuid.UUID
    parent_id: uuid.UUID | None
    parent_name: str | None
    name: str
    slug: str
    description: str | None
    display_order: int
    status: str
    attributes: list[ProductCategoryAttributeResponse] = Field(default_factory=list)
    media: list[ProductCategoryMediaResponse] = Field(default_factory=list)




class UpdateProductCategoryRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    parent_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    display_order: int | None = Field(default=None, ge=0)
    status: ProductCategoryStatus | None = None
    attributes: list[CategoryAttributeInput] = Field(default_factory=list)
    media: list[CategoryMediaInput] = Field(default_factory=list)
