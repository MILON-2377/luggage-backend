
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE_URL = "/api/v1/admin/auth"



@asynccontextmanager
async def test_client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

@pytest.mark.asyncio
async def test_passkey_login_options_rejects_unknown_challenge():
    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={
                "challenge_token": "invalid-challenge-token",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passkey_login_options_rejects_expired_challenge():
    """
    Requires an existing expired MFA_AUTHENTICATION challenge
    with purpose='admin_login'.

    Replace the token with the raw token corresponding to that
    challenge's stored SHA-256 hash.
    """
    expired_challenge_token = "replace-with-expired-challenge-token"

    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={
                "challenge_token": expired_challenge_token,
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_passkey_login_options_rejects_challenge_without_passkey():
    """
    Requires an existing, unexpired MFA_AUTHENTICATION challenge
    whose available_mfa_methods does not contain 'passkey'.
    """
    challenge_token = "replace-with-no-passkey-challenge-token"

    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={
                "challenge_token": challenge_token,
            },
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_passkey_login_options_generates_authentication_options():
    """
    Requires an existing, unexpired MFA_AUTHENTICATION challenge
    with purpose='admin_login' and 'passkey' in available_mfa_methods.

    The associated ACTIVE admin account must have at least one
    active WebAuthn credential.

    Replace the token with the raw token corresponding to the
    challenge's stored SHA-256 hash.
    """
    challenge_token = "replace-with-valid-passkey-challenge-token"

    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={
                "challenge_token": challenge_token,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert "public_key" in body

    public_key = body["public_key"]

    assert public_key["challenge"]
    assert public_key["rpId"]
    assert public_key["allowCredentials"]
    assert public_key["userVerification"] == "required"

    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"


@pytest.mark.asyncio
async def test_passkey_login_options_rejects_missing_challenge_token():
    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_passkey_login_options_rejects_extra_request_fields():
    async with test_client() as client:
        response = await client.post(
            f"{BASE_URL}/login/passkey/options",
            json={
                "challenge_token": "invalid-challenge-token",
                "extra": "not-allowed",
            },
        )

    assert response.status_code == 422
