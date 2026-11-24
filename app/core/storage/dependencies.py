from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, settings
from app.core.contracts.storage.media import AbstractMediaStorage
from app.core.storage.registry import (
    create_media_storage,
    is_media_provider_registered,
)
from app.integrations.media import register_media_providers


def get_settings() -> Settings:
    return settings


@lru_cache(maxsize=1)
def _build_media_storage() -> AbstractMediaStorage:
    app_settings = get_settings()

    if not is_media_provider_registered(app_settings.MEDIA_PROVIDER):
        register_media_providers(app_settings)

    return create_media_storage(app_settings.MEDIA_PROVIDER)


def get_media_storage() -> AbstractMediaStorage:
    return _build_media_storage()


MediaStorageDep = Annotated[AbstractMediaStorage, Depends(get_media_storage)]