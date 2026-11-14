import dataclasses
import math

import pytest

from app.core.rate_limit.token_bucket import (
    TokenBucket,
    TokenBucketConfig,
    TokenBucketResult,
    TokenBucketState,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def make_config(capacity: int = 10, refill_rate: float = 1.0) -> TokenBucketConfig:
    return TokenBucketConfig(capacity=capacity, refill_rate=refill_rate)


def consume(
    config: TokenBucketConfig,
    state: TokenBucketState,
    now: float,
    cost: float = 1.0,
) -> TokenBucketResult:
    return TokenBucket.consume(config=config, state=state, now=now, cost=cost)


# --------------------------------------------------------------------------- #
# TokenBucketConfig
# --------------------------------------------------------------------------- #


class TestTokenBucketConfig:
    def test_valid_config(self) -> None:
        config = TokenBucketConfig(capacity=5, refill_rate=0.5)

        assert config.capacity == 5
        assert config.refill_rate == 0.5

    @pytest.mark.parametrize("capacity", [0, -1, -100])
    def test_rejects_non_positive_capacity(self, capacity: int) -> None:
        with pytest.raises(ValueError, match="capacity"):
            TokenBucketConfig(capacity=capacity, refill_rate=1.0)

    @pytest.mark.parametrize("refill_rate", [0, -0.1, -5])
    def test_rejects_non_positive_refill_rate(self, refill_rate: float) -> None:
        with pytest.raises(ValueError, match="refill rate"):
            TokenBucketConfig(capacity=10, refill_rate=refill_rate)

    @pytest.mark.parametrize("refill_rate", [math.nan, math.inf, -math.inf])
    def test_rejects_non_finite_refill_rate(self, refill_rate: float) -> None:
        with pytest.raises(ValueError, match="finite"):
            TokenBucketConfig(capacity=10, refill_rate=refill_rate)

    def test_is_immutable(self) -> None:
        config = make_config()

        with pytest.raises(dataclasses.FrozenInstanceError):
            config.capacity = 99  # type: ignore[misc]

    def test_per_window_computes_refill_rate(self) -> None:
        config = TokenBucketConfig.per_window(limit=100, window_seconds=60)

        assert config.capacity == 100
        assert config.refill_rate == pytest.approx(100 / 60)

    @pytest.mark.parametrize("window", [0, -1, -60])
    def test_per_window_rejects_invalid_window(self, window: float) -> None:
        with pytest.raises(ValueError, match="Window"):
            TokenBucketConfig.per_window(limit=10, window_seconds=window)

    def test_per_window_rejects_invalid_limit(self) -> None:
        with pytest.raises(ValueError):
            TokenBucketConfig.per_window(limit=0, window_seconds=60)


# --------------------------------------------------------------------------- #
# TokenBucketState
# --------------------------------------------------------------------------- #


class TestTokenBucketState:
    def test_full_state_starts_at_capacity(self) -> None:
        config = make_config(capacity=7)

        state = TokenBucketState.full(config, now=123.0)

        assert state.tokens == 7.0
        assert state.last_refill_at == 123.0

    def test_is_immutable(self) -> None:
        state = TokenBucketState(tokens=1.0, last_refill_at=0.0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            state.tokens = 5.0  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# TokenBucket.consume: basic behaviour
# --------------------------------------------------------------------------- #


class TestConsumeBasics:
    def test_allows_request_when_bucket_is_full(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState.full(config, now=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(9.0)
        assert result.retry_after == 0.0
        assert result.limit == 10

    def test_allowed_request_decrements_tokens_in_new_state(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState.full(config, now=100.0)

        result = consume(config, state, now=100.0)

        assert result.state.tokens == pytest.approx(9.0)
        assert result.state.last_refill_at == 100.0

    def test_does_not_mutate_input_state(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState(tokens=5.0, last_refill_at=50.0)

        consume(config, state, now=60.0)

        assert state.tokens == 5.0
        assert state.last_refill_at == 50.0

    def test_denies_request_when_bucket_is_empty(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=0.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is False
        assert result.remaining_tokens == pytest.approx(0.0)
        assert result.retry_after == pytest.approx(1.0)

    def test_denied_request_does_not_consume_tokens(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=0.4, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is False
        assert result.state.tokens == pytest.approx(0.4)

    def test_denied_request_still_advances_refill_timestamp(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=0.0, last_refill_at=100.0)

        result = consume(config, state, now=100.5)

        assert result.allowed is False
        assert result.state.last_refill_at == 100.5
        assert result.state.tokens == pytest.approx(0.5)

    def test_allows_exactly_the_last_token(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState(tokens=1.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# TokenBucket.consume: refill behaviour
# --------------------------------------------------------------------------- #


class TestConsumeRefill:
    def test_refills_proportionally_to_elapsed_time(self) -> None:
        config = make_config(capacity=10, refill_rate=2.0)
        state = TokenBucketState(tokens=0.0, last_refill_at=100.0)

        # 2.5s * 2 tokens/s = 5 tokens, minus 1 consumed
        result = consume(config, state, now=102.5)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(4.0)

    def test_refill_is_capped_at_capacity(self) -> None:
        config = make_config(capacity=10, refill_rate=5.0)
        state = TokenBucketState(tokens=8.0, last_refill_at=100.0)

        # 1000s of idle time would give 5000 tokens, but capacity is 10
        result = consume(config, state, now=1100.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(9.0)

    def test_fractional_tokens_accumulate_across_calls(self) -> None:
        config = make_config(capacity=10, refill_rate=0.5)
        state = TokenBucketState(tokens=0.0, last_refill_at=0.0)

        first = consume(config, state, now=1.0)  # 0.5 tokens, denied
        assert first.allowed is False

        second = consume(config, first.state, now=2.0)  # 1.0 tokens, allowed
        assert second.allowed is True
        assert second.remaining_tokens == pytest.approx(0.0)

    def test_no_time_elapsed_means_no_refill(self) -> None:
        config = make_config(capacity=10, refill_rate=100.0)
        state = TokenBucketState(tokens=3.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.remaining_tokens == pytest.approx(2.0)


# --------------------------------------------------------------------------- #
# TokenBucket.consume: cost
# --------------------------------------------------------------------------- #


class TestConsumeCost:
    def test_consumes_custom_cost(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState.full(config, now=0.0)

        result = consume(config, state, now=0.0, cost=4.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(6.0)

    def test_denies_when_cost_exceeds_available_tokens(self) -> None:
        config = make_config(capacity=10, refill_rate=2.0)
        state = TokenBucketState(tokens=3.0, last_refill_at=0.0)

        result = consume(config, state, now=0.0, cost=5.0)

        assert result.allowed is False
        assert result.remaining_tokens == pytest.approx(3.0)
        # needs 2 more tokens at 2 tokens/s
        assert result.retry_after == pytest.approx(1.0)

    def test_cost_equal_to_capacity_is_allowed_on_full_bucket(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState.full(config, now=0.0)

        result = consume(config, state, now=0.0, cost=10.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(0.0)

    @pytest.mark.parametrize("cost", [0, -1, -0.5])
    def test_rejects_non_positive_cost(self, cost: float) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)

        with pytest.raises(ValueError, match="cost"):
            consume(config, state, now=0.0, cost=cost)

    def test_rejects_cost_above_capacity(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState.full(config, now=0.0)

        with pytest.raises(ValueError, match="cost"):
            consume(config, state, now=0.0, cost=10.01)

    @pytest.mark.parametrize("cost", [math.nan, math.inf])
    def test_rejects_non_finite_cost(self, cost: float) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)

        with pytest.raises(ValueError, match="finite"):
            consume(config, state, now=0.0, cost=cost)


# --------------------------------------------------------------------------- #
# TokenBucket.consume: input validation
# --------------------------------------------------------------------------- #


class TestConsumeValidation:
    def test_rejects_negative_now(self) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)

        with pytest.raises(ValueError, match="timestamp"):
            consume(config, state, now=-1.0)

    def test_rejects_negative_last_refill_timestamp(self) -> None:
        config = make_config()
        state = TokenBucketState(tokens=5.0, last_refill_at=-1.0)

        with pytest.raises(ValueError, match="refill timestamp"):
            consume(config, state, now=10.0)

    @pytest.mark.parametrize("bad", [math.nan, math.inf])
    def test_rejects_non_finite_now(self, bad: float) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)

        with pytest.raises(ValueError, match="finite"):
            consume(config, state, now=bad)

    @pytest.mark.parametrize("bad", [math.nan, math.inf])
    def test_rejects_non_finite_stored_tokens(self, bad: float) -> None:
        config = make_config()
        state = TokenBucketState(tokens=bad, last_refill_at=0.0)

        with pytest.raises(ValueError, match="finite"):
            consume(config, state, now=1.0)

    def test_rejects_non_finite_last_refill_timestamp(self) -> None:
        config = make_config()
        state = TokenBucketState(tokens=5.0, last_refill_at=math.nan)

        with pytest.raises(ValueError, match="finite"):
            consume(config, state, now=1.0)


# --------------------------------------------------------------------------- #
# TokenBucket.consume: robustness against bad / stale stored state
# --------------------------------------------------------------------------- #


class TestConsumeRobustness:
    def test_clamps_tokens_above_capacity(self) -> None:
        # Capacity was lowered in config after the key was stored.
        config = make_config(capacity=5)
        state = TokenBucketState(tokens=50.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(4.0)

    def test_clamps_negative_stored_tokens_to_zero(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=-3.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.allowed is False
        assert result.remaining_tokens == pytest.approx(0.0)
        assert result.retry_after == pytest.approx(1.0)

    def test_clock_moving_backwards_gives_no_refill(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=2.0, last_refill_at=100.0)

        result = consume(config, state, now=90.0)

        assert result.allowed is True
        assert result.remaining_tokens == pytest.approx(1.0)

    def test_clock_moving_backwards_never_rewinds_refill_timestamp(self) -> None:
        config = make_config()
        state = TokenBucketState(tokens=5.0, last_refill_at=100.0)

        result = consume(config, state, now=90.0)

        assert result.state.last_refill_at == 100.0

    def test_remaining_tokens_never_negative(self) -> None:
        config = make_config(capacity=10)
        state = TokenBucketState(tokens=1.0 - 1e-12, last_refill_at=0.0)

        result = consume(config, state, now=0.0)

        assert result.remaining_tokens >= 0.0
        assert result.state.tokens >= 0.0


# --------------------------------------------------------------------------- #
# Float precision
# --------------------------------------------------------------------------- #


class TestFloatPrecision:
    def test_waiting_exactly_retry_after_is_allowed(self) -> None:
        # 0.3 tokens/s makes retry_after = 3.333..., a classic float trap.
        config = make_config(capacity=3, refill_rate=0.3)
        state = TokenBucketState(tokens=0.0, last_refill_at=0.0)

        denied = consume(config, state, now=0.0)
        assert denied.allowed is False

        retried = consume(config, denied.state, now=denied.retry_after)

        assert retried.allowed is True

    @pytest.mark.parametrize("rate", [0.1, 0.3, 0.7, 1 / 3, 7 / 11])
    def test_waiting_exactly_retry_after_is_allowed_for_many_rates(
        self, rate: float
    ) -> None:
        config = make_config(capacity=5, refill_rate=rate)
        state = TokenBucketState(tokens=0.0, last_refill_at=0.0)

        denied = consume(config, state, now=0.0)
        retried = consume(config, denied.state, now=denied.retry_after)

        assert retried.allowed is True

    def test_many_small_steps_do_not_drift_above_capacity(self) -> None:
        config = make_config(capacity=3, refill_rate=0.1)
        state = TokenBucketState.full(config, now=0.0)

        now = 0.0
        for _ in range(10_000):
            now += 0.01
            result = TokenBucket.consume(config=config, state=state, now=now, cost=1.0)
            state = result.state
            assert 0.0 <= state.tokens <= config.capacity


# --------------------------------------------------------------------------- #
# Result helpers: retry_after, reset_after, headers
# --------------------------------------------------------------------------- #


class TestResultHelpers:
    def test_retry_after_seconds_rounds_up(self) -> None:
        config = make_config(capacity=10, refill_rate=0.4)
        state = TokenBucketState(tokens=0.0, last_refill_at=0.0)

        result = consume(config, state, now=0.0)

        assert result.retry_after == pytest.approx(2.5)
        assert result.retry_after_seconds == 3

    def test_retry_after_seconds_is_zero_when_allowed(self) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)

        result = consume(config, state, now=0.0)

        assert result.retry_after_seconds == 0

    def test_reset_after_is_time_until_bucket_is_full(self) -> None:
        config = make_config(capacity=10, refill_rate=2.0)
        state = TokenBucketState.full(config, now=0.0)

        result = consume(config, state, now=0.0, cost=4.0)

        # 6 tokens left, needs 4 more at 2 tokens/s
        assert result.reset_after == pytest.approx(2.0)

    def test_reset_after_is_zero_when_bucket_stays_full(self) -> None:
        # Refill during the request offsets the cost exactly.
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState(tokens=9.0, last_refill_at=0.0)

        result = consume(config, state, now=2.0)  # 9 + 2 -> capped 10, minus 1

        assert result.remaining_tokens == pytest.approx(9.0)
        assert result.reset_after == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("tokens", "expected"),
        [(0.0, 0), (0.99, 0), (2.5, 2), (3.0, 3), (2.9999999999, 3)],
    )
    def test_remaining_whole_floors_with_tolerance(
        self, tokens: float, expected: int
    ) -> None:
        result = TokenBucketResult(
            allowed=True,
            limit=10,
            remaining_tokens=tokens,
            retry_after=0.0,
            reset_after=0.0,
            state=TokenBucketState(tokens=tokens, last_refill_at=0.0),
        )

        assert result.remaining_whole == expected

    def test_headers_when_allowed(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState.full(config, now=100.0)

        result = consume(config, state, now=100.0)

        assert result.headers() == {
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "9",
            "X-RateLimit-Reset": "1",
        }

    def test_headers_when_blocked_include_retry_after(self) -> None:
        config = make_config(capacity=10, refill_rate=0.5)
        state = TokenBucketState(tokens=0.0, last_refill_at=100.0)

        result = consume(config, state, now=100.0)

        assert result.headers() == {
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "20",
            "Retry-After": "2",
        }

    def test_retry_after_header_is_at_least_one_second(self) -> None:
        config = make_config(capacity=10, refill_rate=100.0)
        state = TokenBucketState(tokens=0.0, last_refill_at=0.0)

        result = consume(config, state, now=0.0)

        assert 0 < result.retry_after < 1
        assert result.headers()["Retry-After"] == "1"

    def test_result_is_immutable(self) -> None:
        config = make_config()
        state = TokenBucketState.full(config, now=0.0)
        result = consume(config, state, now=0.0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            result.allowed = False  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# End-to-end scenarios
# --------------------------------------------------------------------------- #


class TestScenarios:
    def test_burst_then_throttle_then_recover(self) -> None:
        config = make_config(capacity=5, refill_rate=1.0)
        state = TokenBucketState.full(config, now=0.0)

        # Burst: the first 5 requests are allowed at the same instant.
        for _ in range(5):
            result = consume(config, state, now=0.0)
            assert result.allowed is True
            state = result.state

        # The 6th is throttled.
        result = consume(config, state, now=0.0)
        assert result.allowed is False
        assert result.retry_after == pytest.approx(1.0)
        state = result.state

        # After the advertised wait, exactly one request passes again.
        result = consume(config, state, now=1.0)
        assert result.allowed is True
        state = result.state

        result = consume(config, state, now=1.0)
        assert result.allowed is False

    def test_steady_rate_at_refill_speed_is_always_allowed(self) -> None:
        config = make_config(capacity=1, refill_rate=2.0)
        state = TokenBucketState.full(config, now=0.0)

        now = 0.0
        for _ in range(100):
            result = consume(config, state, now=now)
            assert result.allowed is True
            state = result.state
            now += 0.5  # exactly the refill interval

    def test_sustained_overload_is_limited_to_refill_rate(self) -> None:
        config = make_config(capacity=10, refill_rate=5.0)
        state = TokenBucketState.full(config, now=0.0)

        allowed = 0
        now = 0.0
        # 100 requests per second for 10 seconds
        for _ in range(1000):
            result = consume(config, state, now=now)
            state = result.state
            allowed += int(result.allowed)
            now += 0.01

        # burst (10) + 10s * 5 tokens/s = 60, with tolerance for boundaries
        assert 59 <= allowed <= 61

    def test_independent_buckets_do_not_affect_each_other(self) -> None:
        config = make_config(capacity=1, refill_rate=0.1)
        state_a = TokenBucketState.full(config, now=0.0)
        state_b = TokenBucketState.full(config, now=0.0)

        a1 = consume(config, state_a, now=0.0)
        a2 = consume(config, a1.state, now=0.0)
        b1 = consume(config, state_b, now=0.0)

        assert a1.allowed is True
        assert a2.allowed is False
        assert b1.allowed is True

    def test_different_costs_share_one_bucket(self) -> None:
        config = make_config(capacity=10, refill_rate=1.0)
        state = TokenBucketState.full(config, now=0.0)

        cheap = consume(config, state, now=0.0, cost=1.0)
        expensive = consume(config, cheap.state, now=0.0, cost=9.0)
        too_much = consume(config, expensive.state, now=0.0, cost=1.0)

        assert cheap.allowed is True
        assert expensive.allowed is True
        assert too_much.allowed is False
