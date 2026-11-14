local EPSILON = 1e-9

local function is_finite(value)
    return value ~= nil
        and value == value -- false for NaN
        and value ~= math.huge
        and value ~= -math.huge
end

local key = KEYS[1]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local cost = 1

if ARGV[3] ~= nil then
    cost = tonumber(ARGV[3])
end

if not is_finite(capacity) or capacity <= 0 then
    return redis.error_reply("Invalid bucket capacity")
end

if not is_finite(refill_rate) or refill_rate <= 0 then
    return redis.error_reply("Invalid refill rate")
end

if not is_finite(cost) or cost <= 0 or cost > capacity then
    return redis.error_reply("Invalid token cost")
end

local time = redis.call("TIME")
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000

local bucket = redis.call("HMGET", key, "tokens", "last_refill_at")

local tokens = tonumber(bucket[1])
local last_refill_at = tonumber(bucket[2])

-- No key yet, or the stored pair is missing/corrupt: start from a full bucket.
-- tokens and last_refill_at only make sense together, so reset both.
if not is_finite(tokens) or not is_finite(last_refill_at) then
    tokens = capacity
    last_refill_at = now
end

-- Stored value may be stale (capacity was lowered in config) or have drifted.
tokens = math.min(math.max(tokens, 0), capacity)

-- Never refill for negative time (clock adjustment).
local elapsed = math.max(0, now - last_refill_at)

tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
local retry_after = 0

if tokens + EPSILON >= cost then
    allowed = 1
    tokens = math.max(0, tokens - cost)
else
    retry_after = (cost - tokens) / refill_rate
end

local reset_after = (capacity - tokens) / refill_rate

-- Persist on both outcomes: a denied request still advances last_refill_at,
-- otherwise the elapsed time would be counted again on the next call.
redis.call(
    "HSET",
    key,
    "tokens", tokens,
    "last_refill_at", math.max(now, last_refill_at)
)

-- After a full refill the bucket is indistinguishable from "no key", so the
-- key can safely expire once it would have refilled from empty (+1s margin).
redis.call("EXPIRE", key, math.ceil(capacity / refill_rate) + 1)

return {
    allowed,
    string.format("%.17g", tokens),
    string.format("%.17g", retry_after),
    string.format("%.17g", reset_after)
}