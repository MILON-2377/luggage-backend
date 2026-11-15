import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio

from app.integrations.redis.client import redis_manager
from app.integrations.redis.token_bucket_executor import RedisTokenBucketExecutor


@pytest_asyncio.fixture
async def token_bucket():
    await redis_manager.connect()

    executor = RedisTokenBucketExecutor(redis_manager)
    key = f"test:rate-limit:{uuid4().hex}"
    redis_key = f"{executor.key_prefix}:{key}"

    try:
        yield executor, key
    finally:
        await redis_manager.client.delete(redis_key)
        await redis_manager.disconnect()


@pytest.mark.asyncio
async def test_allows_requests_with_available_tokens(token_bucket):
    executor, key = token_bucket

    result = await executor.consume(
        key=key,
        capacity=5,
        refill_rate=1.0,
    )

    assert result.allowed is True
    assert result.remaining_tokens == pytest.approx(4.0)
    assert result.retry_after == 0


@pytest.mark.asyncio
async def test_rejects_requests_when_bucket_is_empty(token_bucket):
    executor, key = token_bucket

    results = []

    for _ in range(6):
        result = await executor.consume(
            key=key,
            capacity=5,
            refill_rate=0.001,
        )
        results.append(result)

    assert sum(result.allowed for result in results) == 5

    rejected = next(result for result in results if not result.allowed)

    assert rejected.remaining_tokens < 0.01
    assert rejected.retry_after > 0


@pytest.mark.asyncio
async def test_concurrent_requests_are_processed_atomically(token_bucket):
    executor, key = token_bucket

    results = await asyncio.gather(
        *[
            executor.consume(
                key=key,
                capacity=5,
                refill_rate=0.0001,
            )
            for _ in range(20)
        ]
    )

    allowed_count = sum(result.allowed for result in results)

    assert allowed_count == 5

    rejected_results = [
        result for result in results if not result.allowed
    ]

    assert len(rejected_results) == 15

    assert all(
        result.remaining_tokens < 0.01
        for result in rejected_results
    )


@pytest.mark.asyncio
async def test_rejected_request_does_not_consume_tokens(token_bucket):
    executor, key = token_bucket

    for _ in range(5):
        await executor.consume(
            key=key,
            capacity=5,
            refill_rate=0.0001,
        )

    rejected = await executor.consume(
        key=key,
        capacity=5,
        refill_rate=0.0001,
    )

    assert rejected.allowed is False
    assert rejected.remaining_tokens < 0.01
    assert rejected.retry_after > 0





@pytest.mark.asyncio
async def test_bucket_refills_after_waiting(token_bucket):
    executor, key = token_bucket

    for _ in range(2):
        result = await executor.consume(
            key=key,
            capacity=2,
            refill_rate=5.0,
        )
        assert result.allowed is True

    await asyncio.sleep(0.25)

    result = await executor.consume(
        key=key,
        capacity=2,
        refill_rate=5.0,
    )

    assert result.allowed is True


@pytest.mark.asyncio
async def test_supports_variable_token_cost(token_bucket):
    executor, key = token_bucket

    result = await executor.consume(
        key=key,
        capacity=5,
        refill_rate=1.0,
        cost=3.0,
    )

    assert result.allowed is True
    assert result.remaining_tokens == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_rejects_cost_greater_than_capacity(token_bucket):
    executor, key = token_bucket

    with pytest.raises(ValueError):
        await executor.consume(
            key=key,
            capacity=5,
            refill_rate=1.0,
            cost=6.0,
        )


@pytest.mark.asyncio
async def test_bucket_state_is_persisted_in_redis(token_bucket):
    executor, key = token_bucket

    await executor.consume(
        key=key,
        capacity=5,
        refill_rate=0.0001,
    )

    redis_key = f"{executor.key_prefix}:{key}"

    bucket = await redis_manager.client.hgetall(redis_key)

    assert "tokens" in bucket
    assert "last_refill_at" in bucket
    assert float(bucket["tokens"]) == pytest.approx(4.0)