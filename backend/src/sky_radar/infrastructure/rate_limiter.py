from sky_radar.infrastructure.cache import RedisCache


class RateLimiter:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        client = self.cache.client
        if not client:
            return True

        redis_key = f"ratelimit:{key}"
        count = await client.incr(redis_key)
        if count == 1:
            await client.expire(redis_key, window_seconds)
        return count <= max_requests
