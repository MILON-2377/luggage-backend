import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, Response
from starlette.requests import Request

import app.core.rate_limit.dependencies as dependencies
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.policies import RateLimitPolicyName
from app.integrations.redis.client import redis_manager
from app.integrations.redis.rate_limit_storage import RedisRateLimitStorage
from app.integrations.redis.token_bucket_executor import RedisTokenBucketExecutor


@pytest_asyncio.fixture
async def rate_limit_storage(monkeypatch):
    await redis_manager.connect()

    executor = RedisTokenBucketExecutor(
        redis_manager,
        key_prefix=f"test:rate-limit:{uuid4().hex}",
    )
    storage = RedisRateLimitStorage(executor)

    monkeypatch.setattr(dependencies, "_storage", storage)

    try:
        yield storage
    finally:
        await redis_manager.disconnect()


def create_request(
    *,
    client_ip: str,
    forwarded_for: str | None = None,
) -> Request:
    headers = []

    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": headers,
            "client": (client_ip, 12345),
            "server": ("testserver", 80),
        }
    )


@pytest.mark.asyncio
async def test_rate_limit_enforces_authentication_policy(rate_limit_storage):
    dependency = rate_limit(RateLimitPolicyName.AUTHENTICATION)
    request = create_request(client_ip="203.0.113.10")

    responses = []

    for _ in range(5):
        response = Response()
        await dependency(request, response)
        responses.append(response)

    assert all(response.headers["X-RateLimit-Limit"] == "5" for response in responses)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(request, Response())

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_concurrent_requests_cannot_exceed_bucket_capacity(
    rate_limit_storage,
):
    dependency = rate_limit(RateLimitPolicyName.AUTHENTICATION)
    request = create_request(client_ip="203.0.113.11")

    async def make_request() -> bool:
        try:
            await dependency(request, Response())
            return True
        except HTTPException as exc:
            if exc.status_code == 429:
                return False
            raise

    results = await asyncio.gather(*(make_request() for _ in range(20)))

    assert sum(results) == 5
    assert results.count(False) == 15


@pytest.mark.asyncio
async def test_untrusted_forwarded_header_cannot_bypass_rate_limit(
    rate_limit_storage,
):
    dependency = rate_limit(RateLimitPolicyName.AUTHENTICATION)

    direct_request = create_request(
        client_ip="203.0.113.12",
    )

    spoofed_request = create_request(
        client_ip="203.0.113.12",
        forwarded_for="198.51.100.99",
    )

    for _ in range(5):
        await dependency(direct_request, Response())

    with pytest.raises(HTTPException) as exc_info:
        await dependency(spoofed_request, Response())

    assert exc_info.value.status_code == 429


def test_authenticated_users_have_independent_rate_limit_identities():
    user_a = uuid4()
    user_b = uuid4()

    request_a = create_request(client_ip="203.0.113.20")
    request_b = create_request(client_ip="203.0.113.20")

    request_a.state.authenticated_user_id = user_a
    request_b.state.authenticated_user_id = user_b

    identity_a = dependencies._get_rate_limit_identity(
        request_a,
        RateLimitPolicyName.AUTHENTICATED_API,
    )
    identity_b = dependencies._get_rate_limit_identity(
        request_b,
        RateLimitPolicyName.AUTHENTICATED_API,
    )

    assert identity_a == f"user:{user_a}"
    assert identity_b == f"user:{user_b}"
    assert identity_a != identity_b


def test_same_authenticated_user_shares_bucket_across_ip_addresses():
    user_id = uuid4()

    request_a = create_request(client_ip="203.0.113.21")
    request_b = create_request(client_ip="203.0.113.22")

    request_a.state.authenticated_user_id = user_id
    request_b.state.authenticated_user_id = user_id

    identity_a = dependencies._get_rate_limit_identity(
        request_a,
        RateLimitPolicyName.AUTHENTICATED_API,
    )
    identity_b = dependencies._get_rate_limit_identity(
        request_b,
        RateLimitPolicyName.AUTHENTICATED_API,
    )

    assert identity_a == identity_b == f"user:{user_id}"


def test_unauthenticated_authenticated_api_request_uses_ip():
    request = create_request(client_ip="203.0.113.23")

    identity = dependencies._get_rate_limit_identity(
        request,
        RateLimitPolicyName.AUTHENTICATED_API,
    )

    assert identity == "ip:203.0.113.23"


def test_other_policies_always_use_ip_identity():
    user_id = uuid4()
    request = create_request(client_ip="203.0.113.24")
    request.state.authenticated_user_id = user_id

    identity = dependencies._get_rate_limit_identity(
        request,
        RateLimitPolicyName.AUTHENTICATION,
    )

    assert identity == "ip:203.0.113.24"
