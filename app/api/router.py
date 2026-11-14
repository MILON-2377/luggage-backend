from fastapi import APIRouter

from app.api.v1.public.router import public_router

api_router = APIRouter()


api_router.include_router(public_router, prefix="/public")
