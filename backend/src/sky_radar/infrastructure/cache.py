import json
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis
from loguru import logger

from sky_radar.api.exceptions import CacheError


class RedisCache:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: redis.Redis | None = None
        self.lock_key = "sky_radar:sync_lock"
        self.tle_cache_key = "sky_radar:tle_cache"
        self.lock_ttl = 300
        self.cache_ttl = 43200

    async def connect(self):
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        logger.info("Redis connection established")

    async def disconnect(self):
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

    async def acquire_lock(self) -> bool:
        if not self.client:
            raise CacheError("acquire_lock", "Redis client not initialized")

        acquired = await self.client.set(self.lock_key, "1", nx=True, ex=self.lock_ttl)
        if acquired:
            logger.info("Distributed lock acquired")
        else:
            logger.debug("Distributed lock already held by another worker")
        return bool(acquired)

    async def release_lock(self):
        if not self.client:
            raise CacheError("release_lock", "Redis client not initialized")

        await self.client.delete(self.lock_key)
        logger.info("Distributed lock released")

    async def clear_stale_lock(self):
        if not self.client:
            return
        await self.client.delete(self.lock_key)
        logger.info("Cleared stale sync lock")

    async def cache_tle_data(self, satellites: list[dict[str, Any]]):
        if not self.client:
            raise CacheError("cache_tle_data", "Redis client not initialized")

        data = {
            "satellites": satellites,
            "cached_at": datetime.now(tz=UTC).isoformat(),
        }
        await self.client.setex(
            self.tle_cache_key,
            self.cache_ttl,
            json.dumps(data),
        )
        logger.info(f"Cached {len(satellites)} satellites to Redis")

    async def get_cached_tle_data(self) -> dict[str, Any] | None:
        if not self.client:
            raise CacheError("get_cached_tle_data", "Redis client not initialized")

        data = await self.client.get(self.tle_cache_key)
        if not data:
            return None

        return json.loads(data)

    async def is_cache_fresh(self, max_age_hours: int = 12) -> bool:
        cached = await self.get_cached_tle_data()
        if not cached:
            return False

        cached_at = datetime.fromisoformat(cached["cached_at"])
        age = datetime.now(tz=UTC) - cached_at
        return age < timedelta(hours=max_age_hours)
