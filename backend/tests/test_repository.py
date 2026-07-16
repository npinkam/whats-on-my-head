from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from sky_radar.models import Satellite
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.schemas.satellite import SatelliteUpsertData


async def test_get_all():
    repo = SatelliteRepository()
    session = AsyncMock()

    sat1 = MagicMock(spec=Satellite)
    sat1.name = "ISS"
    sat2 = MagicMock(spec=Satellite)
    sat2.name = "NOAA 19"

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [sat1, sat2]
    mock_result.scalars.return_value = mock_scalars
    session.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_all(session)

    assert len(result) == 2
    assert result[0].name == "ISS"
    assert result[1].name == "NOAA 19"


async def test_bulk_upsert_empty():
    repo = SatelliteRepository()
    session = AsyncMock()

    await repo.bulk_upsert(session, [])

    session.execute.assert_not_called()
    session.commit.assert_not_called()


async def test_bulk_upsert_creates_records():
    repo = SatelliteRepository()
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()

    now = datetime.now(tz=UTC)
    satellites = [
        SatelliteUpsertData(
            name="ISS",
            tle_line1="1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
            tle_line2="2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",
            epoch=now,
        ),
    ]

    await repo.bulk_upsert(session, satellites)

    session.execute.assert_called_once()
    session.commit.assert_called_once()
