from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import AsyncSessionLocal
from app.modules.catalog.models.product_category import ProductCategory


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.execute(
                delete(ProductCategory).where(
                    ProductCategory.slug.in_(
                        ["travel-bags", "carry-on-bags"]
                    )
                )
            )
            await session.commit()