import httpx
import pytest
from fastapi import FastAPI, Request

from app.core.middleware.authentication import AuthenticationMiddleware
from app.core.rate_limit.dependencies import _get_rate_limit_identity
from app.core.rate_limit.policies import RateLimitPolicyName


class FakeJWTProvider:
    def decode_access_token(self, token: str) -> dict:
        if token != "valid-access-token":
            raise ValueError("Invalid token.")

        return {
            "sub": "12345678-1234-5678-1234-567812345678",
            "sid": "87654321-4321-8765-4321-876543218765",
            "type": "access",
        }


class FakeCookieService:
    def get_access_token(self, request: Request) -> str | None:
        return request.cookies.get("access_token")


@pytest.mark.asyncio
async def test_authentication_middleware_populates_user_identity():
    app = FastAPI()

    app.add_middleware(
        AuthenticationMiddleware,
        jwt_provider=FakeJWTProvider(),
        cookie_service=FakeCookieService(),
    )

    @app.get("/test")
    async def test_endpoint(request: Request):
        identity = _get_rate_limit_identity(
            request,
            RateLimitPolicyName.AUTHENTICATED_API,
        )

        return {
            "user_id": str(request.state.authenticated_user_id),
            "session_id": str(request.state.authenticated_session_id),
            "identity": identity,
        }

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": "valid-access-token"},
    ) as client:
        response = await client.get("/test")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "12345678-1234-5678-1234-567812345678",
        "session_id": "87654321-4321-8765-4321-876543218765",
        "identity": "user:12345678-1234-5678-1234-567812345678",
    }


@pytest.mark.asyncio
async def test_invalid_access_token_falls_back_to_ip_identity():
    app = FastAPI()

    app.add_middleware(
        AuthenticationMiddleware,
        jwt_provider=FakeJWTProvider(),
        cookie_service=FakeCookieService(),
    )

    @app.get("/test")
    async def test_endpoint(request: Request):
        identity = _get_rate_limit_identity(
            request,
            RateLimitPolicyName.AUTHENTICATED_API,
        )

        return {
            "user_id": request.state.authenticated_user_id,
            "session_id": request.state.authenticated_session_id,
            "identity": identity,
        }

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": "invalid-access-token"},
    ) as client:
        response = await client.get(
            "/test",
            headers={"X-Forwarded-For": "198.51.100.10"},
        )

    assert response.status_code == 200
    assert response.json()["user_id"] is None
    assert response.json()["session_id"] is None
    assert response.json()["identity"].startswith("ip:")