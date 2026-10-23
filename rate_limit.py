"""Shared Redis limiter with a safe in-process fallback."""

import time
from collections import defaultdict, deque

import config

_local_buckets = defaultdict(deque)
_redis = None


def _redis_client():
    global _redis
    if _redis is not None:
        return _redis
    if not config.REDIS_URL:
        return None
    try:
        import redis
        _redis = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
        _redis.ping()
        return _redis
    except Exception:
        _redis = False
        return None


def allow(key: str, limit: int | None = None, window_seconds: int = 60) -> bool:
    limit = limit or config.RATE_LIMIT_PER_MINUTE
    client = _redis_client()
    if client:
        bucket_key = f"pai:rate:{key}"
        try:
            count = client.incr(bucket_key)
            if count == 1:
                client.expire(bucket_key, window_seconds)
            return count <= limit
        except Exception:
            pass

    now = time.monotonic()
    bucket = _local_buckets[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True
