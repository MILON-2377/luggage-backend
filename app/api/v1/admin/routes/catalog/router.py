from fastapi import APIRouter

from app.api.v1.admin.routes.catalog.product_category import (
    router as product_category_router,
)

router = APIRouter(prefix="/catalog", tags=["Product Catalog"])

router.include_router(product_category_router)