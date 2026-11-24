import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from ipaddress import IPv4Address
from typing import Any

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.contracts.storage.errors import (
    AssetMimeTypeMismatchError,
    AssetNotFoundError,
    MediaStorageError,
)
from app.core.contracts.storage.media import (
    AbstractMediaStorage,
    SignedUpload,
    VerifiedAsset,
)
from app.core.storage.dependencies import get_media_storage
from app.main import app
from app.modules.authentication.dependencies.current_admin import get_current_admin
from app.modules.authentication.enums import AdminUserStatus
from app.modules.authentication.models import AdminUser
from app.modules.media.enums import MediaType, StorageProvider
from app.modules.media.models.media_asset import MediaAsset
from app.modules.media.models.media_file import MediaFile
from app.modules.media.models.media_storage_location import MediaStorageLocation


def unique_ip() -> str:
    return str(IPv4Address(0x0A000000 | (uuid.uuid4().int & 0x00FFFFFF)))


@dataclass
class FakeMediaStorage(AbstractMediaStorage):
    uploads: dict[str, dict[str, Any]] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)
    fail_delete: bool = False

    @property
    def provider(self) -> StorageProvider:
        return StorageProvider.CLOUDINARY

    def simulate_upload(
        self,
        public_id: str,
        *,
        mime_type: str = "image/png",
        file_format: str = "png",
        file_size: int = 2048,
        width: int | None = 800,
        height: int | None = 600,
    ) -> None:
        self.uploads[public_id] = {
            "mime_type": mime_type,
            "file_format": file_format,
            "file_size": file_size,
            "width": width,
            "height": height,
        }

    async def create_signed_upload(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        mime_type: str,
        expires_in: int,
    ) -> SignedUpload:
        return SignedUpload(
            upload_url="https://fake.storage.test/upload",
            upload_params={"public_id": public_id, "signature": "fake"},
        )

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> dict[str, Any]:
        if public_id not in self.uploads:
            raise AssetNotFoundError(public_id)
        return self.uploads[public_id]

    async def delete_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
    ) -> None:
        if self.fail_delete:
            raise MediaStorageError("Simulated provider failure.")
        self.uploads.pop(public_id, None)
        self.deleted.append(public_id)

    async def verify_asset(
        self,
        *,
        public_id: str,
        media_type: MediaType,
        expected_mime_type: str,
        expected_file_format: str | None = None,
    ) -> VerifiedAsset:

        metadata = await self.get_asset_metadata(
            public_id=public_id,
            media_type=media_type,
        )

        if metadata["mime_type"] != expected_mime_type:
            raise AssetMimeTypeMismatchError(
                expected=expected_mime_type,
                actual=metadata["mime_type"],
            )

        return VerifiedAsset(
            public_id=public_id,
            resource_type="image",
            mime_type=metadata["mime_type"],
            file_format=metadata["file_format"],
            file_size=metadata["file_size"],
            width=metadata["width"],
            height=metadata["height"],
            secure_url=f"https://fake.storage.test/{public_id}",
        )


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest_asyncio.fixture
async def session_factory(settings):
    engine = create_async_engine(settings.DATABASE_URL)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def fake_storage() -> FakeMediaStorage:
    return FakeMediaStorage()


@pytest_asyncio.fixture
async def admin(session_factory):

    now = datetime.now(UTC)

    admin_user = AdminUser(
        id=uuid.uuid4(),
        email=f"media-admin-{uuid.uuid4().hex[:12]}@example.com",
        password_hash=PasswordHasher().hash("CorrectPassword123!"),
        status=AdminUserStatus.ACTIVE,
        email_verified_at=now,
        password_changed_at=now,
        failed_login_attempts=0,
        locked_until=None,
    )

    async with session_factory() as session:
        session.add(admin_user)
        await session.commit()

    yield admin_user

    async with session_factory() as session:
        asset_ids = select(MediaAsset.id).where(MediaAsset.uploaded_by == admin_user.id)
        file_ids = select(MediaFile.id).where(MediaFile.media_asset_id.in_(asset_ids))

        # media_storage_locations.media_file_id is ON DELETE RESTRICT,
        # so locations must go first.
        await session.execute(
            delete(MediaStorageLocation).where(
                MediaStorageLocation.media_file_id.in_(file_ids)
            )
        )
        await session.execute(
            delete(MediaFile).where(MediaFile.media_asset_id.in_(asset_ids))
        )
        await session.execute(
            delete(MediaAsset).where(MediaAsset.uploaded_by == admin_user.id)
        )
        await session.execute(delete(AdminUser).where(AdminUser.id == admin_user.id))
        await session.commit()


async def _build_client(monkeypatch, fake_storage):
    monkeypatch.setattr(
        "app.core.rate_limit.dependencies.get_client_ip",
        lambda request: unique_ip(),
    )
    app.dependency_overrides[get_media_storage] = lambda: fake_storage


@pytest_asyncio.fixture
async def client(monkeypatch, fake_storage, admin):
    await _build_client(monkeypatch, fake_storage)
    app.dependency_overrides[get_current_admin] = lambda: admin

    try:
        async with LifespanManager(app, startup_timeout=30, shutdown_timeout=30):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                yield c
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client(monkeypatch, fake_storage):
    await _build_client(monkeypatch, fake_storage)

    try:
        async with LifespanManager(app, startup_timeout=30, shutdown_timeout=30):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                yield c
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def load_state(session_factory):
    async def _load(media_asset_id: uuid.UUID):
        async with session_factory() as session:
            asset = (
                await session.execute(
                    select(MediaAsset).where(MediaAsset.id == media_asset_id)
                )
            ).scalar_one()
            media_file = (
                await session.execute(
                    select(MediaFile).where(MediaFile.media_asset_id == media_asset_id)
                )
            ).scalar_one()
            location = (
                await session.execute(
                    select(MediaStorageLocation).where(
                        MediaStorageLocation.media_file_id == media_file.id
                    )
                )
            ).scalar_one()
            return asset, media_file, location

    return _load
