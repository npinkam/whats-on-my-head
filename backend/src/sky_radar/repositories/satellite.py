from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sky_radar.models import Satellite
from sky_radar.schemas.satellite import SatelliteUpsertData


class SatelliteRepository:
    async def get_max_updated_at(self, session: AsyncSession) -> datetime | None:
        result = await session.execute(select(func.max(Satellite.updated_at)))
        return result.scalar()

    async def has_fresh_data(self, session: AsyncSession, hours: int = 12) -> bool:
        max_updated = await self.get_max_updated_at(session)
        if max_updated is None:
            return False
        cutoff = datetime.now(tz=UTC).replace(tzinfo=None) - timedelta(hours=hours)
        return max_updated > cutoff

    async def get_all_serialized(self, session: AsyncSession) -> list[dict]:
        result = await session.execute(select(Satellite))
        satellites = list(result.scalars().all())
        return [
            {
                "norad_cat_id": s.norad_cat_id,
                "name": s.name,
                "tle_line1": s.tle_line1,
                "tle_line2": s.tle_line2,
                "epoch": s.epoch.isoformat(),
            }
            for s in satellites
        ]

    async def get_all(self, session: AsyncSession) -> list[Satellite]:
        result = await session.execute(select(Satellite))
        return list(result.scalars().all())

    async def bulk_upsert(
        self,
        session: AsyncSession,
        satellites: list[SatelliteUpsertData],
        batch_size: int = 5000,
    ) -> None:
        if not satellites:
            return

        for i in range(0, len(satellites), batch_size):
            batch = satellites[i : i + batch_size]
            values = [s.model_dump() for s in batch]
            stmt = insert(Satellite).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["norad_cat_id"],
                set_={
                    "name": stmt.excluded.name,
                    "tle_line1": stmt.excluded.tle_line1,
                    "tle_line2": stmt.excluded.tle_line2,
                    "epoch": stmt.excluded.epoch,
                },
            )
            await session.execute(stmt)

        await session.commit()
