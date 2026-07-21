from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from skyfield.api import load

from sky_radar.infrastructure.cache import RedisCache
from sky_radar.infrastructure.rate_limiter import RateLimiter
from sky_radar.infrastructure.websocket_manager import ConnectionManager
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.tracker import SatelliteTracker


@asynccontextmanager
async def noop_lifespan(app: FastAPI):
    yield


@pytest.fixture
def ts():
    return load.timescale()


@pytest.fixture
def sample_tle():
    return (
        "ISS (ZARYA)",
        "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
        "2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",
    )


@pytest.fixture
def sample_tle_list():
    return [
        {
            "norad_cat_id": 25544,
            "name": "ISS (ZARYA)",
            "tle_line1": "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
            "tle_line2": "2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",
        },
        {
            "norad_cat_id": 33591,
            "name": "NOAA 19",
            "tle_line1": "1 33591U 09005A   24001.50000000  .00000095  00000-0  65573-4 0  9998",
            "tle_line2": "2 33591  99.1903  33.8564 0013894 101.2758 258.9399 14.12508495776476",
        },
    ]


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock()
    mock.setex = AsyncMock()
    return mock


@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def tracker():
    return SatelliteTracker()


@pytest.fixture
def mock_cache():
    cache = AsyncMock(spec=RedisCache)
    cache.acquire_lock = AsyncMock(return_value=True)
    cache.release_lock = AsyncMock()
    cache.cache_tle_data = AsyncMock()
    cache.get_cached_tle_data = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def mock_repository():
    repo = AsyncMock(spec=SatelliteRepository)
    repo.get_all = AsyncMock(return_value=[])
    repo.bulk_upsert = AsyncMock()
    return repo


@pytest.fixture
def mock_manager():
    manager = MagicMock(spec=ConnectionManager)
    manager.active_connections = []
    manager.client_locations = {}
    manager.connect = AsyncMock()
    manager.disconnect = MagicMock()
    manager.send_personal_message = AsyncMock()
    manager.get_client_location = MagicMock(return_value=(0.0, 0.0))
    manager.update_client_location = MagicMock()
    return manager


@pytest.fixture
def test_client():
    from sky_radar.main import app

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan

    fake_redis = fakeredis.FakeAsyncRedis()
    mock_cache = AsyncMock(spec=RedisCache)
    mock_cache.client = fake_redis
    mock_cache.connect = AsyncMock()
    mock_cache.disconnect = AsyncMock()

    mock_engine = AsyncMock()
    mock_engine.dispose = AsyncMock()

    mock_session_factory = MagicMock()
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    app.state.cache = mock_cache
    app.state.db_engine = mock_engine
    app.state.db_session = mock_session_factory
    app.state.manager = ConnectionManager()
    app.state.repository = SatelliteRepository()
    app.state.tracker = SatelliteTracker()
    app.state.rate_limiter = RateLimiter(mock_cache)

    mock_celes_trak = AsyncMock()
    mock_celes_trak.close = AsyncMock()
    app.state.celes_trak_client = mock_celes_trak

    with TestClient(app) as client:
        yield client

    app.router.lifespan_context = original_lifespan
