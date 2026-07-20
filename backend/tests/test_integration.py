import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from sky_radar.infrastructure.cache import RedisCache
from sky_radar.models import Base
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.tle_sync import TLESyncService
from sky_radar.services.tracker import SatelliteTracker


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as rc:
        yield rc


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pc:
        yield pc


@pytest.fixture
async def real_cache(redis_container):
    url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
    cache = RedisCache(url)
    await cache.connect()
    await cache.clear_stale_lock()
    yield cache
    await cache.disconnect()


@pytest.fixture
async def real_session(postgres_container):
    port = postgres_container.get_exposed_port(5432)
    host = postgres_container.get_container_host_ip()
    db_url = f"postgresql+asyncpg://test:test@{host}:{port}/test"
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with _session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_tle_response():
    return [
        (
            "ISS (ZARYA)",
            "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
            "2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",
        ),
        (
            "NOAA 19",
            "1 33591U 09005A   24001.50000000  .00000095  00000-0  65573-4 0  9998",
            "2 33591  99.1903  33.8564 0013894 101.2758 258.9399 14.12508495776476",
        ),
    ]


async def test_tle_sync_with_real_redis_and_pg(real_cache, real_session, sample_tle_response):
    tracker = SatelliteTracker()
    repository = SatelliteRepository()

    mock_client = AsyncMock()
    mock_client.fetch_active_artifact = AsyncMock(return_value=sample_tle_response)

    tle_sync = TLESyncService(mock_client, real_cache, repository, tracker)

    count = await tle_sync.sync(real_session)

    assert count == 2
    assert len(tracker.get_satellite_objects()) == 2

    result = await real_session.execute(text("SELECT COUNT(*) FROM satellites"))
    row = result.one()
    assert row[0] == 2

    result = await real_session.execute(text("SELECT name FROM satellites ORDER BY name"))
    rows = result.all()
    assert rows[0][0] == "ISS (ZARYA)"
    assert rows[1][0] == "NOAA 19"


async def test_tle_sync_idempotent(real_cache, real_session, sample_tle_response):
    tracker = SatelliteTracker()
    repository = SatelliteRepository()

    mock_client = AsyncMock()
    mock_client.fetch_active_artifact = AsyncMock(return_value=sample_tle_response)

    tle_sync = TLESyncService(mock_client, real_cache, repository, tracker)

    count1 = await tle_sync.sync(real_session)
    assert count1 == 2

    # Second call hits fresh data path, no fetch
    count2 = await tle_sync.sync(real_session)
    assert count2 == 2

    result = await real_session.execute(text("SELECT COUNT(*) FROM satellites"))
    assert result.one()[0] == 2


async def test_tle_sync_redis_lock(real_cache, real_session, sample_tle_response):
    mock_client = AsyncMock()
    mock_client.fetch_active_artifact = AsyncMock(return_value=sample_tle_response)

    locked = await real_cache.acquire_lock()
    assert locked is True
    real_cache.release_lock = AsyncMock()

    second_lock = await real_cache.acquire_lock()
    assert second_lock is False


async def test_broadcast_with_real_redis(redis_container, sample_tle_response):
    url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
    cache = RedisCache(url)
    await cache.connect()
    await cache.clear_stale_lock()

    tracker = SatelliteTracker()

    mock_client = AsyncMock()
    mock_client.fetch_active_artifact = AsyncMock(return_value=sample_tle_response)

    mock_repo = AsyncMock()
    mock_repo.has_fresh_data = AsyncMock(return_value=False)
    mock_repo.bulk_upsert = AsyncMock()
    tle_sync = TLESyncService(mock_client, cache, mock_repo, tracker)
    await tle_sync.sync(AsyncMock())

    positions = tracker.calculate_positions_batch(
        tracker.get_satellite_objects(), 40.7128, -74.0060, only_visible=False
    )

    message = tracker.serialize_for_websocket(positions)
    raw = json.dumps(message)
    parsed = json.loads(raw)

    assert "timestamp" in parsed
    assert "satellites" in parsed
    for sat in parsed["satellites"]:
        assert isinstance(sat["is_visible"], bool)

    await cache.disconnect()
