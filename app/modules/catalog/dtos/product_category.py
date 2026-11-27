import uuid
from dataclasses import dataclass

from app.modules.catalog.enums import CategoryMediaRole, ProductCategoryStatus


@dataclass(frozen=True, slots=True)
class CreateCategoryAttributeCommand:
    attribute_id: uuid.UUID
    is_required: bool
    display_order: int


@dataclass(frozen=True, slots=True)
class CreateCategoryMediaCommand:
    media_asset_id: uuid.UUID
    media_role: CategoryMediaRole
    display_order: int


@dataclass(frozen=True, slots=True)
class CreateProductCategoryCommand:
    parent_id: uuid.UUID | None
    name: str
    description: str | None
    display_order: int
    attributes: tuple[CreateCategoryAttributeCommand, ...]
    media: tuple[CreateCategoryMediaCommand, ...]


@dataclass(frozen=True, slots=True)
class CreateProductCategoryResult:
    category_id: uuid.UUID
    name: str
    slug: str
    status: str


@dataclass(frozen=True, slots=True)
class ProductCategoryMediaItem:
    media_asset_id: uuid.UUID
    media_role: CategoryMediaRole
    display_order: int
    url: str


@dataclass(frozen=True, slots=True)
class ProductCategoryTreeItem:
    category_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    display_order: int
    status: str
    media: tuple[ProductCategoryMediaItem, ...]
    children: tuple["ProductCategoryTreeItem", ...]


@dataclass(frozen=True, slots=True)
class ProductCategoryListResult:
    items: tuple[ProductCategoryTreeItem, ...]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool


@dataclass(frozen=True, slots=True)
class ProductCategoryAttributeItem:
    attribute_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    data_type: str
    unit: str | None
    is_custom_allowed: bool
    is_required: bool
    display_order: int


@dataclass(frozen=True, slots=True)
class ProductCategoryDetailResult:
    category_id: uuid.UUID
    parent_id: uuid.UUID | None
    parent_name: str | None
    name: str
    slug: str
    description: str | None
    display_order: int
    status: str
    attributes: tuple[ProductCategoryAttributeItem, ...]
    media: tuple[ProductCategoryMediaItem, ...]


@dataclass(frozen=True, slots=True)
class UpdateProductCategoryCommand:
    category_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str | None = None
    status: ProductCategoryStatus | None = None
    description: str | None = None
    display_order: int | None = None
    attributes: tuple[CreateCategoryAttributeCommand, ...] | None = None
    media: tuple[CreateCategoryMediaCommand, ...] | None = None
    provided_fields: frozenset[str] = frozenset()
