import math
from dataclasses import dataclass

from app.integrations.redis.client import RedisManager

_EPSILON = 1e-9
_SCRIPT_NAME = "token_bucket"
_RESPONSE_LENGTH = 4


@dataclass(frozen=True, slots=True)
class RedisTokenBucketResult:
    allowed: bool
    limit: int
    remaining_tokens: float
    retry_after: float
    reset_after: float

    @property
    def retry_after_seconds(self) -> int:
        return math.ceil(self.retry_after)

    @property
    def remaining_whole(self) -> int:
        return math.floor(self.remaining_tokens + _EPSILON)

    def headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining_whole),
            "X-RateLimit-Reset": str(math.ceil(self.reset_after)),
        }

        if not self.allowed:
            headers["Retry-After"] = str(max(1, self.retry_after_seconds))

        return headers


class RedisTokenBucketExecutor:
    def __init__(
        self,
        redis_manager: RedisManager,
        key_prefix: str = "rate_limit:token_bucket",
    ) -> None:
        if not key_prefix:
            raise ValueError("Key prefix cannot be empty.")

        self.redis_manager = redis_manager
        self.key_prefix = key_prefix

    async def consume(
        self,
        *,
        key: str,
        capacity: int,
        refill_rate: float,
        cost: float = 1.0,
    ) -> RedisTokenBucketResult:
        if not key:
            raise ValueError("Bucket key cannot be empty.")

        if not math.isfinite(capacity) or capacity <= 0:
            raise ValueError("Bucket capacity must be a finite number greater than zero.")

        if not math.isfinite(refill_rate) or refill_rate <= 0:
            raise ValueError("Refill rate must be a finite number greater than zero.")

        if not math.isfinite(cost) or cost <= 0 or cost > capacity:
            raise ValueError("Token cost must be positive and cannot exceed capacity.")

        script = self.redis_manager.scripts.get(_SCRIPT_NAME)

        response = await script(
            keys=[f"{self.key_prefix}:{key}"],
            args=[capacity, refill_rate, cost],
        )

        if not isinstance(response, (list, tuple)) or len(response) != _RESPONSE_LENGTH:
            raise RuntimeError("Unexpected response from the token bucket script.")

        allowed, remaining_tokens, retry_after, reset_after = response

        return RedisTokenBucketResult(
            allowed=bool(int(allowed)),
            limit=int(capacity),
            remaining_tokens=float(remaining_tokens),
            retry_after=float(retry_after),
            reset_after=float(reset_after),
        )