import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

import app.core.database.models
from app.api.router import api_router
from app.core.config import settings
from app.core.errors.error_handlers import register_error_handlers
from app.core.logging.config import setup_logging
from app.core.middleware.request_id import RequestIDMiddleware
from app.core.middleware.request_logging import RequestLoggingMiddleware
from app.integrations.redis.client import redis_manager

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting application: %s", settings.APP_NAME)

    async with httpx.AsyncClient() as http_client:
        application.state.http_client = http_client

        try:
            await redis_manager.connect()
            logger.info("Redis connection established")

            yield

        finally:
            await redis_manager.disconnect()
            logger.info("Redis connection closed")

    logger.info("Application shutdown completed.")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestIDMiddleware)

    register_error_handlers(application=application)

    application.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
    )

    return application


app = create_application()
