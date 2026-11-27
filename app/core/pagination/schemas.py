from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_previous: bool
    has_next: bool

    model_config = ConfigDict(frozen=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMetadata

    model_config = ConfigDict(frozen=True)