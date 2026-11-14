import pytest

from app.core.rate_limit.policies import (
    RATE_LIMIT_POLICIES,
    RateLimitPolicy,
    RateLimitPolicyName,
    get_rate_limit_policy,
)


def test_all_rate_limit_policies_are_registered():
    assert set(RATE_LIMIT_POLICIES) == set(RateLimitPolicyName)


@pytest.mark.parametrize(
    ("name", "capacity", "refill_rate"),
    [
        (RateLimitPolicyName.PUBLIC_API, 60, 1.0),
        (RateLimitPolicyName.AUTHENTICATION, 5, 1 / 180),
        (RateLimitPolicyName.INQUIRY_SUBMISSION, 3, 1 / 600),
        (RateLimitPolicyName.PAYMENT, 10, 1 / 30),
    ],
)
def test_policy_configuration(name, capacity, refill_rate):
    policy = get_rate_limit_policy(name)

    assert policy.name == name
    assert policy.capacity == capacity
    assert policy.refill_rate == pytest.approx(refill_rate)


def test_get_rate_limit_policy_returns_registered_policy():
    policy = get_rate_limit_policy(RateLimitPolicyName.PUBLIC_API)

    assert policy is RATE_LIMIT_POLICIES[RateLimitPolicyName.PUBLIC_API]


def test_unknown_policy_raises_value_error():
    with pytest.raises(ValueError, match="Unknown rate limit policy"):
        get_rate_limit_policy("unknown")


@pytest.mark.parametrize(
    ("capacity", "refill_rate"),
    [
        (0, 1.0),
        (-1, 1.0),
        (10, 0),
        (10, -1.0),
    ],
)
def test_policy_rejects_invalid_configuration(capacity, refill_rate):
    with pytest.raises(ValueError):
        RateLimitPolicy(
            name=RateLimitPolicyName.PUBLIC_API,
            capacity=capacity,
            refill_rate=refill_rate,
        )