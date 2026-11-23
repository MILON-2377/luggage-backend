
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.admin.routes.authentication.me import router
from app.modules.authentication.dependencies.current_admin import get_current_admin
from app.modules.authentication.enums import AdminUserStatus
from app.modules.authentication.models import AdminUser


@pytest.mark.asyncio
async def test_get_me_returns_current_admin():
    admin_user = AdminUser(
        id=uuid4(),
        email="admin@example.com",
        status=AdminUserStatus.ACTIVE,
        email_verified_at=datetime.now(UTC),
        last_login_at=datetime.now(UTC),
    )

    app = FastAPI()
    app.include_router(router, prefix="/auth")

    app.dependency_overrides[get_current_admin] = lambda: admin_user

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/auth/me")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"

        payload = response.json()
        assert payload["id"] == str(admin_user.id)
        assert payload["email"] == admin_user.email
        assert payload["status"] == admin_user.status.value
    finally:
        app.dependency_overrides.clear()