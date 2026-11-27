import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.modules.catalog.enums import ProductCategoryStatus
from app.modules.catalog.models.product_category import ProductCategory


@pytest.mark.asyncio
async def test_create_product_category(
    client: AsyncClient,
    db_session,
) -> None:
    name = f"Travel Bags {uuid.uuid4().hex[:8]}"
    expected_slug = name.lower().replace(" ", "-")

    payload = {
        "parent_id": None,
        "name": name,
        "description": "Travel bags category",
        "display_order": 1,
        "attributes": [],
        "media": [],
    }

    response = await client.post(
        "/api/v1/admin/catalog/categories",
        json=payload,
    )

    assert response.status_code == 201, response.json()

    result = response.json()

    assert uuid.UUID(result["category_id"])
    assert result["name"] == name
    assert result["slug"] == expected_slug
    assert result["status"] == ProductCategoryStatus.DRAFT.value

    statement = select(ProductCategory).where(
        ProductCategory.id == uuid.UUID(result["category_id"]),
    )
    category = await db_session.scalar(statement)

    assert category is not None
    assert category.name == name
    assert category.slug == expected_slug
    assert category.description == payload["description"]
    assert category.display_order == payload["display_order"]


@pytest.mark.asyncio
async def test_create_product_category_rejects_duplicate_slug(
    client: AsyncClient,
    db_session,
) -> None:
    name = f"Travel Bags {uuid.uuid4().hex[:8]}"
    slug = name.lower().replace(" ", "-")

    db_session.add(
        ProductCategory(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            display_order=0,
        )
    )
    await db_session.commit()

    response = await client.post(
        "/api/v1/admin/catalog/categories",
        json={
            "name": name,
            "display_order": 0,
            "attributes": [],
            "media": [],
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_product_category_rejects_missing_parent(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/admin/catalog/categories",
        json={
            "parent_id": str(uuid.uuid4()),
            "name": "Carry-on Bags",
            "display_order": 0,
            "attributes": [],
            "media": [],
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_product_category_rejects_invalid_payload(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/admin/catalog/categories",
        json={
            "name": "",
            "display_order": -1,
            "attributes": [],
            "media": [],
        },
    )

    assert response.status_code == 422