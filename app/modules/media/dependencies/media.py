from typing import Annotated

from app.core.generators.dependencies import get_id_generator
from fastapi import Depends

from app.core.config import Settings
from app.core.contracts.generators.id_generator import AbstractIDGenerator
from app.core.database.unit_of_work import UnitOfWork
from app.core.storage.dependencies import MediaStorageDep, get_settings
from app.modules.media.contracts.services.media import AbstractMediaService
from app.modules.media.dependencies.uow import get_media_uow
from app.modules.media.services.media import MediaService


def get_media_service(
    uow: Annotated[UnitOfWork, Depends(get_media_uow)],
    id_generator: Annotated[AbstractIDGenerator, Depends(get_id_generator)],
    storage: MediaStorageDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AbstractMediaService:
    return MediaService(
        uow=uow,
        id_generator=id_generator,
        storage=storage,
        settings=settings,
    )