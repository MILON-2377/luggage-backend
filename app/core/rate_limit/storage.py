from typing import Protocol

from app.core.rate_limit.models import RateLimitDecision


class RateLimitStorage(Protocol):
    async def consume(
        self,
        *,
        key: str,
        capacity: int,
        refill_rate: float,
        cost: float = 1.0,
    ) -> RateLimitDecision:
        ...