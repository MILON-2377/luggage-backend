import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

import app.core.rate_limit.dependencies as dependencies
from app.core.rate_limit.dependencies import rate_limit
from app.core.rate_limit.models import RateLimitDecision
from app.core.rate_limit.policies import RateLimitPolicyName


class FakeStorage:
    def __init__(self, decision: RateLimitDecision):
        self.decision = decision
        self.calls = []

    async def consume(self, **kwargs):
        self.calls.append(kwargs)
        return self.decision


def create_request(
    peer_ip: str = "203.0.113.10",
) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "client": (peer_ip, 12345),
            "server": ("testserver", 80),
        }
    )


@pytest.mark.asyncio
async def test_rate_limit_allows_request_and_sets_headers(monkeypatch):
    storage = FakeStorage(
        RateLimitDecision(
            allowed=True,
            limit=60,
            remaining_tokens=59.8,
            retry_after=0,
            reset_after=1.2,
        )
    )
    monkeypatch.setattr(dependencies, "_storage", storage)

    dependency = rate_limit(RateLimitPolicyName.PUBLIC_API)
    response = Response()

    result = await dependency(create_request(), response)

    assert result is None
    assert len(storage.calls) == 1
    assert storage.calls[0]["key"] == "public_api:203.0.113.10"
    assert storage.calls[0]["capacity"] == 60

    assert response.headers["X-RateLimit-Limit"] == "60"
    assert response.headers["X-RateLimit-Remaining"] == "59"
    assert response.headers["X-RateLimit-Reset"] == "2"
    assert "Retry-After" not in response.headers


@pytest.mark.asyncio
async def test_rate_limit_rejects_excessive_requests_with_headers(monkeypatch):
    storage = FakeStorage(
        RateLimitDecision(
            allowed=False,
            limit=5,
            remaining_tokens=0,
            retry_after=12.5,
            reset_after=30,
        )
    )
    monkeypatch.setattr(dependencies, "_storage", storage)

    dependency = rate_limit(RateLimitPolicyName.AUTHENTICATION)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(create_request(), Response())

    exception = exc_info.value

    assert exception.status_code == 429
    assert exception.detail == "Too many requests. Please try again later."
    assert exception.headers["Retry-After"] == "13"
    assert exception.headers["X-RateLimit-Limit"] == "5"
    assert exception.headers["X-RateLimit-Remaining"] == "0"
    assert exception.headers["X-RateLimit-Reset"] == "30"


def test_rate_limit_rejects_invalid_cost():
    with pytest.raises(ValueError):
        rate_limit(
            RateLimitPolicyName.PUBLIC_API,
            cost=100,
        )