import math
from collections.abc import Callable
from uuid import UUID

from fastapi import HTTPException, Request, Response, status

from app.core.rate_limit.client_identity import get_client_ip
from app.core.rate_limit.policies import (
    RateLimitPolicyName,
    get_rate_limit_policy,
)
from app.integrations.redis.client import redis_manager
from app.integrations.redis.rate_limit_storage import RedisRateLimitStorage
from app.integrations.redis.token_bucket_executor import RedisTokenBucketExecutor

_storage = RedisRateLimitStorage(RedisTokenBucketExecutor(redis_manager))


def _build_rate_limit_headers(
    *,
    limit: int,
    remaining_tokens: float,
    reset_after: float,
    retry_after: float | None = None,
) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(
            max(0, math.floor(remaining_tokens + 1e-9))
        ),
        "X-RateLimit-Reset": str(max(0, math.ceil(reset_after))),
    }

    if retry_after is not None:
        headers["Retry-After"] = str(max(1, math.ceil(retry_after)))

    return headers


def _get_rate_limit_identity(
    request: Request,
    policy_name: RateLimitPolicyName,
) -> str:
    if policy_name == RateLimitPolicyName.AUTHENTICATED_API:
        user_id = getattr(
            request.state,
            "authenticated_user_id",
            None,
        )

        if isinstance(user_id, UUID):
            return f"user:{user_id}"

    return f"ip:{get_client_ip(request)}"


def rate_limit(
    policy_name: RateLimitPolicyName,
    *,
    cost: float = 1.0,
) -> Callable:
    policy = get_rate_limit_policy(policy_name)

    if cost <= 0 or cost > policy.capacity:
        raise ValueError(
            "Rate limit cost must be positive and cannot exceed capacity."
        )

    async def dependency(
        request: Request,
        response: Response,
    ) -> None:
        identity = _get_rate_limit_identity(request, policy_name)
        key = f"{policy.name.value}:{identity}"

        decision = await _storage.consume(
            key=key,
            capacity=policy.capacity,
            refill_rate=policy.refill_rate,
            cost=cost,
        )

        headers = _build_rate_limit_headers(
            limit=decision.limit,
            remaining_tokens=decision.remaining_tokens,
            reset_after=decision.reset_after,
            retry_after=(
                decision.retry_after if not decision.allowed else None
            ),
        )

        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers=headers,
            )

        response.headers.update(headers)

    return dependency