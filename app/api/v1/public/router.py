from fastapi import APIRouter

from app.api.v1.public.health import router as health_router

public_router = APIRouter()


public_router.include_router(health_router)
