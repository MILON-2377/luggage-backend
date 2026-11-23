import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address

import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.main import app
from app.modules.authentication.enums import AdminUserStatus
from app.modules.authentication.models import AdminTotpCredential, AdminUser

LOGIN_URL = "/api/v1/admin/auth/login"
WRONG_PASSWORD = "IncorrectPassword123!"
CORRECT_PASSWORD = "CorrectPassword123!"


@dataclass
class AdminAccount:
    id: uuid.UUID
    email: str
    password: str


def unique_ip() -> str:
    return str(IPv4Address(0x0A000000 | (uuid.uuid4().int & 0x00FFFFFF)))


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest_asyncio.fixture
async def session_factory(settings):
    engine = create_async_engine(settings.DATABASE_URL)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(unique_ip(), 50000)),
            base_url="http://test",
        ) as c:
            yield c


@pytest_asyncio.fixture
async def create_admin(session_factory):
    created_ids: list[uuid.UUID] = []
    hasher = PasswordHasher()

    async def _create(
        *,
        password: str | None = CORRECT_PASSWORD,
        status: AdminUserStatus = AdminUserStatus.ACTIVE,
        with_totp: bool = True,
    ) -> AdminAccount:
        admin_id = uuid.uuid4()
        email = f"admin-{uuid.uuid4().hex[:12]}@example.com"

        async with session_factory() as session:
            session.add(
                AdminUser(
                    id=admin_id,
                    email=email,
                    password_hash=(
                        hasher.hash(password) if password is not None else None
                    ),
                    status=status,
                    failed_login_attempts=0,
                    locked_until=None,
                )
            )
            await session.flush()

            if with_totp:
                session.add(
                    AdminTotpCredential(
                        id=uuid.uuid4(),
                        admin_user_id=admin_id,
                        secret_encrypted="test-secret",
                        verified_at=datetime.now(UTC),
                        revoked_at=None,
                    )
                )

            await session.commit()

        created_ids.append(admin_id)
        return AdminAccount(
            id=admin_id,
            email=email,
            password=password or "",
        )

    yield _create

    if created_ids:
        async with session_factory() as session:
            await session.execute(
                delete(AdminTotpCredential).where(
                    AdminTotpCredential.admin_user_id.in_(created_ids)
                )
            )
            await session.execute(
                delete(AdminUser).where(AdminUser.id.in_(created_ids))
            )
            await session.commit()


@pytest_asyncio.fixture
async def expire_lock(session_factory):
    async def _expire(admin_id: uuid.UUID) -> None:
        async with session_factory() as session:
            await session.execute(
                update(AdminUser)
                .where(AdminUser.id == admin_id)
                .values(locked_until=datetime.now(UTC) - timedelta(minutes=1))
            )
            await session.commit()

    return _expire


@pytest_asyncio.fixture
async def get_failed_attempts(session_factory):
    async def _get(admin_id: uuid.UUID) -> int:
        async with session_factory() as session:
            result = await session.execute(
                select(AdminUser.failed_login_attempts).where(
                    AdminUser.id == admin_id
                )
            )
            return result.scalar_one()

    return _get


async def login(client: AsyncClient, email: str, password: str):
    return await client.post(
        LOGIN_URL,
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(client):
    response = await login(client, "unknown@example.com", WRONG_PASSWORD)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_LOGIN_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(client, create_admin):
    admin = await create_admin()

    response = await login(client, admin.email, WRONG_PASSWORD)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_LOGIN_CREDENTIALS"


@pytest.mark.asyncio
async def test_unknown_email_and_wrong_password_return_same_error(
    client, create_admin
):
    admin = await create_admin()

    unknown = await login(client, "unknown@example.com", WRONG_PASSWORD)
    wrong = await login(client, admin.email, WRONG_PASSWORD)

    assert unknown.status_code == wrong.status_code
    assert unknown.json()["error"]["code"] == wrong.json()["error"]["code"]


@pytest.mark.asyncio
async def test_login_normalizes_email_case(client, create_admin):
    admin = await create_admin()

    response = await login(client, admin.email.upper(), admin.password)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_creates_mfa_challenge(client, create_admin):
    admin = await create_admin()

    response = await login(client, admin.email, admin.password)

    assert response.status_code == 200

    body = response.json()

    assert body["challenge_token"]
    assert body["expires_at"]
    assert body["available_mfa_methods"]
    assert set(body["available_mfa_methods"]).issubset(
        {"passkey", "totp", "recovery_code"}
    )

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"

    assert "access_token" not in body
    assert "refresh_token" not in body


@pytest.mark.asyncio
async def test_login_locks_account_after_max_failed_attempts(
    client, create_admin, settings
):
    admin = await create_admin()
    max_attempts = settings.ADMIN_LOGIN_MAX_FAILED_ATTEMPTS

    for _ in range(max_attempts - 1):
        response = await login(client, admin.email, WRONG_PASSWORD)

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_LOGIN_CREDENTIALS"

    response = await login(client, admin.email, WRONG_PASSWORD)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    locked_response = await login(client, admin.email, admin.password)

    assert locked_response.status_code == 401
    assert locked_response.json()["error"]["code"] == "ACCOUNT_LOCKED"


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempts(
    client, create_admin, get_failed_attempts, settings
):
    admin = await create_admin()
    failures = settings.ADMIN_LOGIN_MAX_FAILED_ATTEMPTS - 1

    for _ in range(failures):
        await login(client, admin.email, WRONG_PASSWORD)

    assert await get_failed_attempts(admin.id) == failures

    response = await login(client, admin.email, admin.password)

    assert response.status_code == 200
    assert await get_failed_attempts(admin.id) == 0


@pytest.mark.asyncio
async def test_login_succeeds_after_lock_expires(
    client, create_admin, expire_lock, settings
):
    admin = await create_admin()

    for _ in range(settings.ADMIN_LOGIN_MAX_FAILED_ATTEMPTS):
        await login(client, admin.email, WRONG_PASSWORD)

    await expire_lock(admin.id)

    response = await login(client, admin.email, admin.password)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_failed_attempt_after_lock_expiry_does_not_relock_immediately(
    client, create_admin, expire_lock, get_failed_attempts, settings
):
    admin = await create_admin()

    for _ in range(settings.ADMIN_LOGIN_MAX_FAILED_ATTEMPTS):
        await login(client, admin.email, WRONG_PASSWORD)

    await expire_lock(admin.id)

    response = await login(client, admin.email, WRONG_PASSWORD)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_LOGIN_CREDENTIALS"
    assert await get_failed_attempts(admin.id) == 1


@pytest.mark.asyncio
async def test_login_rejects_account_without_password(client, create_admin):
    admin = await create_admin(
        password=None,
        status=AdminUserStatus.INVITED,
        with_totp=False,
    )

    response = await login(client, admin.email, "SomePassword123!")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_ELIGIBLE_FOR_LOGIN"


@pytest.mark.asyncio
async def test_login_rejects_inactive_account(client, create_admin):
    admin = await create_admin(status=AdminUserStatus.SUSPENDED)

    response = await login(client, admin.email, admin.password)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_ELIGIBLE_FOR_LOGIN"


@pytest.mark.asyncio
async def test_login_rejects_account_without_enrolled_mfa(client, create_admin):
    admin = await create_admin(with_totp=False)

    response = await login(client, admin.email, admin.password)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_NOT_ELIGIBLE_FOR_LOGIN"