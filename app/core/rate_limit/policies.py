from dataclasses import dataclass
from enum import StrEnum

from app.core.errors.base import InternalError


class RateLimitPolicyName(StrEnum):
    PUBLIC_API = "public_api"
    AUTHENTICATION = "authentication"
    INQUIRY_SUBMISSION = "inquiry_submission"
    PAYMENT = "payment"


class RedisFailureMode(StrEnum):
    FAIL_OPEN = "fail_open"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    name: RateLimitPolicyName
    capacity: int
    refill_rate: float
    redis_failure_mode: RedisFailureMode

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Rate limit capacity must be greater than zero.")

        if self.refill_rate <= 0:
            raise ValueError("Rate limit refill rate must be greater than zero.")


RATE_LIMIT_POLICIES: dict[RateLimitPolicyName, RateLimitPolicy] = {
    RateLimitPolicyName.PUBLIC_API: RateLimitPolicy(
        name=RateLimitPolicyName.PUBLIC_API,
        capacity=60,
        refill_rate=1.0,
        redis_failure_mode=RedisFailureMode.FAIL_OPEN,
    ),
    RateLimitPolicyName.AUTHENTICATION: RateLimitPolicy(
        name=RateLimitPolicyName.AUTHENTICATION,
        capacity=5,
        refill_rate=1 / 180,
        redis_failure_mode=RedisFailureMode.FAIL_CLOSED,
    ),
    RateLimitPolicyName.INQUIRY_SUBMISSION: RateLimitPolicy(
        name=RateLimitPolicyName.INQUIRY_SUBMISSION,
        capacity=3,
        refill_rate=1 / 600,
        redis_failure_mode=RedisFailureMode.FAIL_CLOSED,
    ),
    RateLimitPolicyName.PAYMENT: RateLimitPolicy(
        name=RateLimitPolicyName.PAYMENT,
        capacity=10,
        refill_rate=1 / 30,
        redis_failure_mode=RedisFailureMode.FAIL_CLOSED,
    ),
}


def get_rate_limit_policy(
    name: RateLimitPolicyName,
) -> RateLimitPolicy:
    try:
        return RATE_LIMIT_POLICIES[name]
    except KeyError as exc:
        raise InternalError(f"Unknown rate limit policy: {name}") from exc
