import math
from dataclasses import dataclass

# is not rejected again because of 0.9999999999 < 1.0.
_EPSILON = 1e-9


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")


@dataclass(frozen=True, slots=True)
class TokenBucketConfig:
    """
    capacity:    maximum tokens the bucket can hold (the burst size).
    refill_rate: tokens added per second.
    """

    capacity: int
    refill_rate: float

    def __post_init__(self) -> None:
        _require_finite("Token bucket capacity", self.capacity)
        _require_finite("Token refill rate", self.refill_rate)

        if self.capacity <= 0:
            raise ValueError("Token bucket capacity must be greater than zero.")

        if self.refill_rate <= 0:
            raise ValueError("Token refill rate must be greater than zero.")

    @classmethod
    def per_window(cls, limit: int, window_seconds: float) -> "TokenBucketConfig":
        """e.g. per_window(100, 60) -> 100 requests per minute, burst of 100."""
        if window_seconds <= 0:
            raise ValueError("Window must be greater than zero.")

        return cls(capacity=limit, refill_rate=limit / window_seconds)


@dataclass(frozen=True, slots=True)
class TokenBucketState:
    tokens: float
    last_refill_at: float

    @classmethod
    def full(cls, config: TokenBucketConfig, now: float) -> "TokenBucketState":
        """State for a client seen for the first time (no key in Redis yet)."""
        return cls(tokens=float(config.capacity), last_refill_at=now)


@dataclass(frozen=True, slots=True)
class TokenBucketResult:
    allowed: bool
    limit: int
    remaining_tokens: float
    retry_after: float  # seconds until `cost` tokens are available (0 if allowed)
    reset_after: float  # seconds until the bucket is completely full
    state: TokenBucketState

    @property
    def retry_after_seconds(self) -> int:
        """Whole seconds, for the HTTP Retry-After header."""
        return math.ceil(self.retry_after)

    @property
    def remaining_whole(self) -> int:
        """Whole requests left, for the X-RateLimit-Remaining header."""
        return int(math.floor(self.remaining_tokens + _EPSILON))

    def headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining_whole),
            "X-RateLimit-Reset": str(math.ceil(self.reset_after)),
        }

        if not self.allowed:
            headers["Retry-After"] = str(max(1, self.retry_after_seconds))

        return headers


class TokenBucket:
    @staticmethod
    def consume(
        *,
        config: TokenBucketConfig,
        state: TokenBucketState,
        now: float,
        cost: float = 1.0,
    ) -> TokenBucketResult:
        _require_finite("Current timestamp", now)
        _require_finite("Token count", state.tokens)
        _require_finite("Last refill timestamp", state.last_refill_at)
        _require_finite("Token cost", cost)

        if now < 0:
            raise ValueError("Current timestamp cannot be negative.")

        if state.last_refill_at < 0:
            raise ValueError("Last refill timestamp cannot be negative.")

        if cost <= 0 or cost > config.capacity:
            raise ValueError("Token cost must be positive and cannot exceed capacity.")

        # Stored state may be slightly off (float drift) or stale (capacity was
        # lowered in config after the key was written). Clamp instead of raising,
        # otherwise one config change would break every existing bucket.
        current_tokens = min(max(state.tokens, 0.0), float(config.capacity))

        # Clock moved backwards (NTP adjustment, multi-server skew): no refill.
        elapsed = max(0.0, now - state.last_refill_at)

        refilled_tokens = min(
            float(config.capacity),
            current_tokens + elapsed * config.refill_rate,
        )

        allowed = refilled_tokens + _EPSILON >= cost

        remaining_tokens = (
            max(0.0, refilled_tokens - cost) if allowed else refilled_tokens
        )

        retry_after = 0.0 if allowed else (cost - refilled_tokens) / config.refill_rate

        reset_after = (config.capacity - remaining_tokens) / config.refill_rate

        new_state = TokenBucketState(
            tokens=remaining_tokens,
            last_refill_at=max(now, state.last_refill_at),
        )

        return TokenBucketResult(
            allowed=allowed,
            limit=config.capacity,
            remaining_tokens=remaining_tokens,
            retry_after=retry_after,
            reset_after=reset_after,
            state=new_state,
        )
