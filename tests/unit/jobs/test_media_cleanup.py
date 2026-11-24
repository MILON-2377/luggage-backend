from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.media_cleanup import run_media_cleanup


@pytest.mark.asyncio
async def test_run_media_cleanup_manages_uow_lifecycle_and_runs_service():
    fake_uow = MagicMock()
    uow_gen = MagicMock()
    uow_gen.__anext__ = AsyncMock(return_value=fake_uow)
    uow_gen.aclose = AsyncMock()

    cleanup_result = SimpleNamespace(
        stale_pending_found=2,
        stale_pending_deleted=2,
        deletion_pending_found=1,
        deletion_pending_resumed=1,
        failed=0,
    )
    cleanup_service_instance = MagicMock()
    cleanup_service_instance.run = AsyncMock(return_value=cleanup_result)

    with (
        patch("app.jobs.media_cleanup:get_uow", return_value=uow_gen),
        patch("app.jobs.media_cleanup:register_media_repositories") as register_repos,
        patch("app.jobs.media_cleanup:get_id_generator", return_value=MagicMock()),
        patch("app.jobs.media_cleanup:get_media_storage", return_value=MagicMock()),
        patch("app.jobs.media_cleanup:MediaService", return_value=MagicMock()),
        patch(
            "app.jobs.media_cleanup:MediaCleanupService",
            return_value=cleanup_service_instance,
        ),
    ):
        await run_media_cleanup()

    uow_gen.__anext__.assert_awaited_once()
    register_repos.assert_called_once_with(fake_uow)
    cleanup_service_instance.run.assert_awaited_once()
    uow_gen.aclose.assert_awaited_once()