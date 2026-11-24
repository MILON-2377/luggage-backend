import uuid

import pytest

from app.modules.media.enums import MediaStatus, StorageLocationStatus

BASE_URL = "/api/v1/admin/media"

UPLOAD_PAYLOAD = {
    "original_filename": "photo.png",
    "media_type": "image",
    "mime_type": "image/png",
    "file_size": 2048,
}


async def create_upload(client, **overrides):
    return await client.post(
        f"{BASE_URL}/uploads",
        json={**UPLOAD_PAYLOAD, **overrides},
    )


async def create_and_upload(client, fake_storage, load_state, **overrides):
    response = await create_upload(client, **overrides)
    assert response.status_code == 201

    media_asset_id = uuid.UUID(response.json()["media_asset_id"])
    _, _, location = await load_state(media_asset_id)

    fake_storage.simulate_upload(location.storage_key)

    return media_asset_id, location.storage_key


# ---------- create upload ----------


@pytest.mark.asyncio
async def test_create_upload_requires_authentication(anon_client):
    response = await create_upload(anon_client)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_upload_returns_signed_upload(client, admin, load_state):
    response = await create_upload(client)

    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"

    body = response.json()
    assert body["upload_url"]
    assert body["upload_params"]["signature"]

    asset, media_file, location = await load_state(uuid.UUID(body["media_asset_id"]))

    assert asset.status == MediaStatus.PENDING
    assert asset.uploaded_by == admin.id
    assert asset.original_filename == "photo.png"
    assert media_file.mime_type == "image/png"
    assert location.status == StorageLocationStatus.PENDING
    assert location.is_primary is False
    assert location.storage_key == body["upload_params"]["public_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"file_size": 0},
        {"mime_type": "not a mime"},
        {"original_filename": "   "},
        {"media_type": "audio"},
    ],
)
async def test_create_upload_rejects_invalid_payload(client, overrides):
    response = await create_upload(client, **overrides)

    assert response.status_code == 422


# ---------- confirm upload ----------


@pytest.mark.asyncio
async def test_confirm_upload_requires_authentication(anon_client):
    response = await anon_client.post(f"{BASE_URL}/{uuid.uuid4()}/confirm")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_upload_marks_asset_ready(client, fake_storage, load_state):
    media_asset_id, storage_key = await create_and_upload(
        client, fake_storage, load_state
    )

    response = await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ready"
    assert body["file_size"] == 2048
    assert body["width"] == 800
    assert body["url"] == f"https://fake.storage.test/{storage_key}"

    asset, media_file, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.READY
    assert media_file.file_size == 2048
    assert location.status == StorageLocationStatus.READY
    assert location.is_primary is True


@pytest.mark.asyncio
async def test_confirm_upload_unknown_asset_returns_404(client):
    response = await client.post(f"{BASE_URL}/{uuid.uuid4()}/confirm")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEDIA_ASSET_NOT_FOUND"


# tests/integrations/media/test_admin_media.py (replace test_confirm_before_upload_keeps_asset_pending)
@pytest.mark.asyncio
async def test_confirm_before_upload_keeps_asset_pending(client, load_state):
    create_response = await create_upload(client)
    media_asset_id = uuid.UUID(create_response.json()["media_asset_id"])

    response = await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MEDIA_STORAGE_ASSET_NOT_FOUND"

    asset, _, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.PENDING
    assert location.status == StorageLocationStatus.PENDING


@pytest.mark.asyncio
async def test_confirm_twice_returns_conflict(client, fake_storage, load_state):
    media_asset_id, _ = await create_and_upload(client, fake_storage, load_state)

    first = await client.post(f"{BASE_URL}/{media_asset_id}/confirm")
    second = await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "MEDIA_NOT_PENDING"


@pytest.mark.asyncio
async def test_confirm_with_mime_mismatch_marks_asset_failed(
    client, fake_storage, load_state
):
    create_response = await create_upload(client)
    media_asset_id = uuid.UUID(create_response.json()["media_asset_id"])
    _, _, location = await load_state(media_asset_id)

    fake_storage.simulate_upload(
        location.storage_key,
        mime_type="image/jpeg",
        file_format="jpg",
    )

    response = await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MEDIA_ASSET_MIME_TYPE_MISMATCH"

    asset, _, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.FAILED
    assert location.status == StorageLocationStatus.FAILED
    assert location.storage_key in fake_storage.deleted


# ---------- delete ----------


@pytest.mark.asyncio
async def test_delete_requires_authentication(anon_client):
    response = await anon_client.delete(f"{BASE_URL}/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_removes_remote_file_and_soft_deletes_rows(
    client, fake_storage, load_state
):
    media_asset_id, storage_key = await create_and_upload(
        client, fake_storage, load_state
    )
    await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    response = await client.delete(f"{BASE_URL}/{media_asset_id}")

    assert response.status_code == 204
    assert storage_key in fake_storage.deleted

    asset, _, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.DELETED
    assert asset.deleted_at is not None
    assert location.status == StorageLocationStatus.DELETED
    assert location.is_primary is False


@pytest.mark.asyncio
async def test_delete_unknown_asset_returns_404(client):
    response = await client.delete(f"{BASE_URL}/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_twice_returns_404(client, fake_storage, load_state):
    media_asset_id, _ = await create_and_upload(client, fake_storage, load_state)
    await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    first = await client.delete(f"{BASE_URL}/{media_asset_id}")
    second = await client.delete(f"{BASE_URL}/{media_asset_id}")

    assert first.status_code == 204
    assert second.status_code == 404


@pytest.mark.asyncio
async def test_delete_can_resume_after_provider_failure(
    client, fake_storage, load_state
):
    media_asset_id, storage_key = await create_and_upload(
        client, fake_storage, load_state
    )
    await client.post(f"{BASE_URL}/{media_asset_id}/confirm")

    fake_storage.fail_delete = True
    failed = await client.delete(f"{BASE_URL}/{media_asset_id}")

    assert failed.status_code == 502

    asset, _, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.DELETION_PENDING
    assert location.status == StorageLocationStatus.DELETION_PENDING

    fake_storage.fail_delete = False
    retried = await client.delete(f"{BASE_URL}/{media_asset_id}")

    assert retried.status_code == 204
    assert storage_key in fake_storage.deleted

    asset, _, location = await load_state(media_asset_id)

    assert asset.status == MediaStatus.DELETED
    assert location.status == StorageLocationStatus.DELETED
