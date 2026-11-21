from fastapi import APIRouter

from app.api.v1.admin.routes.authentication.router import (
    router as authentication_router,
)

admin_router = APIRouter(prefix="/admin")

admin_router.include_router(authentication_router)