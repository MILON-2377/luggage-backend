import asyncio
import logging

from app.core.config import settings
from app.core.database.dependencies import get_uow
from app.core.generators.dependencies import get_id_generator
from app.core.storage.dependencies import get_media_storage
from app.modules.media.repositories.registry import register_media_repositories
from app.modules.media.services.media import MediaService
from app.modules.media.services.media_cleanup import MediaCleanupService

logger = logging.getLogger(__name__)


async def run_media_cleanup() -> None:
    uow_gen = get_uow()
    uow = await anext(uow_gen)
    try:
        register_media_repositories(uow)

        media_service = MediaService(
            uow=uow,
            id_generator=get_id_generator(),
            storage=get_media_storage(),
            settings=settings,
        )
        cleanup_service = MediaCleanupService(
            uow=uow,
            media_service=media_service,
            settings=settings,
        )

        result = await cleanup_service.run()
    finally:
        await uow_gen.aclose()

    logger.info(
        "Media cleanup finished: stale_pending=%d/%d deleted, "
        "deletion_pending=%d/%d resumed, failed=%d",
        result.stale_pending_deleted,
        result.stale_pending_found,
        result.deletion_pending_resumed,
        result.deletion_pending_found,
        result.failed,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_media_cleanup())


if __name__ == "__main__":
    main()