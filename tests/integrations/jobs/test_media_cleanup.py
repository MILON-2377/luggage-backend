from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.jobs import media_cleanup as media_cleanup_job
from app.modules.media.enums import MediaStatus, MediaType
from app.modules.media.models.media_asset import MediaAsset


@pytest.mark.asyncio
async def test_run_media_cleanup_processes_stale_pending_and_deletion_pending(
    db_session,
):
    now = datetime.now(UTC)
    stale_created_at = now - timedelta(
        seconds=settings.MEDIA_PENDING_UPLOAD_TTL_SECONDS + 60
    )
    past_deleted_at = now - timedelta(
        seconds=settings.MEDIA_DELETION_RETRY_AFTER_SECONDS + 60
    )

    stale_pending_asset = MediaAsset(
        original_filename="stale-upload.jpg",
        media_type=MediaType.IMAGE,
        status=MediaStatus.PENDING,
        created_at=stale_created_at,
    )
    deletion_pending_asset = MediaAsset(
        original_filename="to-delete.jpg",
        media_type=MediaType.IMAGE,
        status=MediaStatus.DELETION_PENDING,
        deleted_at=past_deleted_at,
    )

    db_session.add_all([stale_pending_asset, deletion_pending_asset])
    await db_session.commit()
    await db_session.refresh(stale_pending_asset)
    await db_session.refresh(deletion_pending_asset)

    created_ids = [stale_pending_asset.id, deletion_pending_asset.id]
    fake_storage = MagicMock()
    fake_storage.delete = AsyncMock(return_value=None)

    try:
        with patch.object(
            media_cleanup_job,
            "get_media_storage",
            return_value=fake_storage,
        ):
            await media_cleanup_job.run_media_cleanup()

        db_session.expire_all()

        refreshed_stale = await db_session.get(MediaAsset, stale_pending_asset.id)
        refreshed_deletion = await db_session.get(MediaAsset, deletion_pending_asset.id)

        assert refreshed_stale is not None
        assert refreshed_stale.status in {
            MediaStatus.DELETED,
            MediaStatus.DELETION_PENDING,
        }
        assert refreshed_deletion is not None
        assert refreshed_deletion.status == MediaStatus.DELETED

        remaining = (await db_session.execute(select(MediaAsset))).scalars().all()
        assert len(remaining) >= 2
    finally:
        db_session.expire_all()
        for asset_id in created_ids:
            row = await db_session.get(MediaAsset, asset_id)
            if row is not None:
                await db_session.delete(row)
        await db_session.commit()