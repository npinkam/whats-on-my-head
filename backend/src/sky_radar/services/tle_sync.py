from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from sky_radar.infrastructure.cache import RedisCache
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.schemas.satellite import SatelliteUpsertData
from sky_radar.services.celestrak import CelesTrakClient
from sky_radar.services.tracker import SatelliteTracker


class TLESyncService:
    def __init__(
        self,
        client: CelesTrakClient,
        cache: RedisCache,
        repository: SatelliteRepository,
        tracker: SatelliteTracker,
    ):
        self.client = client
        self.cache = cache
        self.repository = repository
        self.tracker = tracker

    async def sync(self, session: AsyncSession) -> int:
        if await self.repository.has_fresh_data(session):
            logger.info("DB data is fresh (<12h), loading from DB")
            satellites_data = await self.repository.get_all_serialized(session)
            if satellites_data:
                await self.cache.cache_tle_data(satellites_data)
                self.tracker.update_satellites(satellites_data)
                logger.info(f"Loaded {len(satellites_data)} satellites from DB")
            return len(satellites_data)

        if not await self.cache.acquire_lock():
            logger.info("Another worker is syncing TLE data")
            return 0

        try:
            tles = await self.client.fetch_active_artifact()
            satellites_data = [
                SatelliteUpsertData(
                    name=name,
                    tle_line1=line1,
                    tle_line2=line2,
                    epoch=datetime.now(tz=UTC).replace(tzinfo=None),
                )
                for name, line1, line2 in tles
            ]

            if satellites_data:
                await self.repository.bulk_upsert(session, satellites_data)
                serialized = [s.model_dump(mode="json") for s in satellites_data]
                await self.cache.cache_tle_data(serialized)
                self.tracker.update_satellites(serialized)
                logger.info(f"Synced {len(satellites_data)} satellites")
            else:
                logger.warning("No satellite data fetched")

            return len(satellites_data)

        finally:
            await self.cache.release_lock()
