from app.core.rate_limit.models import RateLimitDecision
from app.core.rate_limit.storage import RateLimitStorage
from app.integrations.redis.token_bucket_executor import (
    RedisTokenBucketExecutor,
)


class RedisRateLimitStorage(RateLimitStorage):
    def __init__(
        self,
        executor: RedisTokenBucketExecutor,
    ) -> None:
        self._executor = executor

    async def consume(
        self,
        *,
        key: str,
        capacity: int,
        refill_rate: float,
        cost: float = 1.0,
    ) -> RateLimitDecision:
        result = await self._executor.consume(
            key=key,
            capacity=capacity,
            refill_rate=refill_rate,
            cost=cost,
        )

        return RateLimitDecision(
            allowed=result.allowed,
            limit=result.limit,
            remaining_tokens=result.remaining_tokens,
            retry_after=result.retry_after,
            reset_after=result.reset_after,
        )