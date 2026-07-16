import contextlib
from unittest.mock import AsyncMock, MagicMock

from sky_radar.api.exceptions import TLEFetchError
from sky_radar.services.broadcaster import BroadcasterService
from sky_radar.services.celestrak import CelesTrakClient
from sky_radar.services.tle_sync import TLESyncService

SAMPLE_TLE_TEXT = """ISS (ZARYA)
1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993
2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999
NOAA 19
1 33591U 09005A   24001.50000000  .00000095  00000-0  65573-4 0  9998
2 33591  99.1903  33.8564 0013894 101.2758 258.9399 14.12508495776476
"""


def test_celestrak_parse_tle():
    client = CelesTrakClient()
    result = client._parse_tle(SAMPLE_TLE_TEXT)

    assert len(result) == 2
    assert result[0][0] == "ISS (ZARYA)"
    assert result[0][1].startswith("1 ")
    assert result[0][2].startswith("2 ")
    assert result[1][0] == "NOAA 19"


def test_celestrak_parse_tle_empty():
    client = CelesTrakClient()
    result = client._parse_tle("")
    assert result == []


def test_celestrak_parse_tle_malformed():
    client = CelesTrakClient()
    result = client._parse_tle("random text\nno tle data here\n")
    assert result == []


async def test_tle_sync_service_sync_success():
    mock_client = AsyncMock(spec=CelesTrakClient)
    mock_client.fetch_tle_group = AsyncMock(
        return_value=[
            (
                "ISS (ZARYA)",
                "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
                "2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",
            ),
        ]
    )

    mock_cache = AsyncMock()
    mock_cache.acquire_lock = AsyncMock(return_value=True)
    mock_cache.release_lock = AsyncMock()
    mock_cache.cache_tle_data = AsyncMock()

    mock_repository = AsyncMock()
    mock_repository.has_fresh_data = AsyncMock(return_value=False)
    mock_repository.bulk_upsert = AsyncMock()

    mock_tracker = MagicMock()
    mock_tracker.update_satellites = MagicMock()

    mock_session = AsyncMock()

    service = TLESyncService(mock_client, mock_cache, mock_repository, mock_tracker)

    count = await service.sync(mock_session)

    assert count == 1
    assert mock_client.fetch_tle_group.call_count == 5
    mock_repository.bulk_upsert.assert_called_once()
    mock_cache.cache_tle_data.assert_called_once()
    mock_tracker.update_satellites.assert_called_once()
    mock_cache.release_lock.assert_called_once()


async def test_tle_sync_service_lock_not_acquired():
    mock_client = AsyncMock(spec=CelesTrakClient)
    mock_cache = AsyncMock()
    mock_cache.acquire_lock = AsyncMock(return_value=False)
    mock_cache.release_lock = AsyncMock()

    mock_repository = AsyncMock()
    mock_repository.has_fresh_data = AsyncMock(return_value=False)
    mock_tracker = MagicMock()
    mock_session = AsyncMock()

    service = TLESyncService(mock_client, mock_cache, mock_repository, mock_tracker)

    count = await service.sync(mock_session)

    assert count == 0
    mock_client.fetch_tle_group.assert_not_called()
    mock_repository.bulk_upsert.assert_not_called()


async def test_tle_sync_service_group_fetch_failure():
    mock_client = AsyncMock(spec=CelesTrakClient)
    mock_client.fetch_tle_group = AsyncMock(side_effect=TLEFetchError("stations", "timeout"))

    mock_cache = AsyncMock()
    mock_cache.acquire_lock = AsyncMock(return_value=True)
    mock_cache.release_lock = AsyncMock()

    mock_repository = AsyncMock()
    mock_repository.has_fresh_data = AsyncMock(return_value=False)
    mock_tracker = MagicMock()
    mock_session = AsyncMock()

    service = TLESyncService(mock_client, mock_cache, mock_repository, mock_tracker)

    count = await service.sync(mock_session)

    assert count == 0
    mock_repository.bulk_upsert.assert_not_called()
    mock_cache.release_lock.assert_called_once()


async def test_tle_sync_service_releases_lock_on_error():
    mock_client = AsyncMock(spec=CelesTrakClient)
    mock_client.fetch_tle_group = AsyncMock(side_effect=RuntimeError("unexpected"))

    mock_cache = AsyncMock()
    mock_cache.acquire_lock = AsyncMock(return_value=True)
    mock_cache.release_lock = AsyncMock()

    mock_repository = AsyncMock()
    mock_repository.has_fresh_data = AsyncMock(return_value=False)
    mock_tracker = MagicMock()
    mock_session = AsyncMock()

    service = TLESyncService(mock_client, mock_cache, mock_repository, mock_tracker)

    with contextlib.suppress(RuntimeError):
        await service.sync(mock_session)

    mock_cache.release_lock.assert_called_once()


async def test_tle_sync_service_skips_fetch_if_fresh():
    mock_client = AsyncMock()
    mock_client.fetch_tle_group = AsyncMock()

    mock_cache = AsyncMock()
    mock_cache.cache_tle_data = AsyncMock()

    mock_repository = AsyncMock()
    mock_repository.has_fresh_data = AsyncMock(return_value=True)
    mock_repository.get_all_serialized = AsyncMock(
        return_value=[
            {
                "name": "ISS (ZARYA)",
                "tle_line1": "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",  # noqa: E501
                "tle_line2": "2 25544  51.6416 208.9163 0006703  40.5765 159.9227 15.72125391999999",  # noqa: E501
                "epoch": "2024-01-01T00:00:00",
            },
        ]
    )

    mock_tracker = MagicMock()
    mock_tracker.update_satellites = MagicMock()

    mock_session = AsyncMock()

    service = TLESyncService(mock_client, mock_cache, mock_repository, mock_tracker)

    count = await service.sync(mock_session)

    assert count == 1
    mock_client.fetch_tle_group.assert_not_called()
    mock_cache.cache_tle_data.assert_called_once()
    mock_tracker.update_satellites.assert_called_once()


def test_broadcaster_service_init():
    mock_tracker = MagicMock()
    mock_manager = MagicMock()
    mock_repository = AsyncMock()

    service = BroadcasterService(mock_tracker, mock_manager, mock_repository)

    assert service.tracker is mock_tracker
    assert service.manager is mock_manager
    assert service.repository is mock_repository
