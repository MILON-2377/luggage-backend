from app.core.rate_limit.models import RateLimitDecision
from app.core.rate_limit.storage import RateLimitStorage


def test_rate_limit_storage_protocol_accepts_implementation():
    class FakeRateLimitStorage:
        async def consume(
            self,
            *,
            key: str,
            capacity: int,
            refill_rate: float,
            cost: float = 1.0,
        ) -> RateLimitDecision:
            return RateLimitDecision(
                allowed=True,
                limit=capacity,
                remaining_tokens=capacity - cost,
                retry_after=0.0,
                reset_after=0.0,
            )

    storage: RateLimitStorage = FakeRateLimitStorage()

    assert storage is not None