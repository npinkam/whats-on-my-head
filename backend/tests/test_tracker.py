from sky_radar.services.tracker import SatelliteTracker


def test_observer_position(sample_tle):
    tracker = SatelliteTracker()
    name, line1, line2 = sample_tle
    satellite = tracker.create_satellite(name, line1, line2)

    position = tracker.calculate_position(
        satellite=satellite,
        latitude=40.7128,
        longitude=-74.0060,
        dt=None,
    )

    assert "latitude" in position
    assert "longitude" in position
    assert "altitude_deg" in position
    assert "azimuth_deg" in position
    assert "range_km" in position
    assert "is_visible" in position
    assert -90 <= position["latitude"] <= 90
    assert -180 <= position["longitude"] <= 180


def test_calculate_positions_batch(tracker, sample_tle_list):
    tracker.update_satellites(sample_tle_list)
    satellites = tracker.get_satellite_objects()

    assert len(satellites) == 2

    positions = tracker.calculate_positions_batch(
        satellites=satellites,
        latitude=40.7128,
        longitude=-74.0060,
    )

    assert len(positions) == 2
    for pos in positions:
        assert "name" in pos
        assert "latitude" in pos
        assert "longitude" in pos
        assert "altitude_deg" in pos
        assert "azimuth_deg" in pos
        assert "range_km" in pos
        assert "is_visible" in pos


def test_only_visible_filtering(tracker, sample_tle_list):
    tracker.update_satellites(sample_tle_list)
    satellites = tracker.get_satellite_objects()

    all_positions = tracker.calculate_positions_batch(
        satellites=satellites,
        latitude=40.7128,
        longitude=-74.0060,
        only_visible=False,
    )

    visible_positions = tracker.calculate_positions_batch(
        satellites=satellites,
        latitude=40.7128,
        longitude=-74.0060,
        only_visible=True,
    )

    assert len(visible_positions) <= len(all_positions)
    for pos in visible_positions:
        assert pos["is_visible"] is True


def test_serialize_for_websocket(tracker, sample_tle_list):
    tracker.update_satellites(sample_tle_list)
    satellites = tracker.get_satellite_objects()

    positions = tracker.calculate_positions_batch(
        satellites=satellites,
        latitude=40.7128,
        longitude=-74.0060,
    )

    result = tracker.serialize_for_websocket(positions)

    assert "timestamp" in result
    assert "observer" in result
    assert "satellites" in result
    assert isinstance(result["timestamp"], str)
    assert "latitude" in result["observer"]
    assert "longitude" in result["observer"]
    assert len(result["satellites"]) == len(positions)

    for sat in result["satellites"]:
        assert "name" in sat
        assert "latitude" in sat
        assert "longitude" in sat
        assert "altitude_deg" in sat
        assert "azimuth_deg" in sat
        assert "range_km" in sat
        assert "is_visible" in sat


def test_serialize_for_websocket_empty(tracker):
    result = tracker.serialize_for_websocket([])

    assert "timestamp" in result
    assert "observer" in result
    assert result["observer"]["latitude"] == 0.0
    assert result["observer"]["longitude"] == 0.0
    assert result["satellites"] == []


def test_update_satellites(tracker, sample_tle_list):
    tracker.update_satellites(sample_tle_list)
    satellites = tracker.get_satellite_objects()

    assert len(satellites) == 2
    names = [s.name for s in satellites]
    assert "ISS (ZARYA)" in names
    assert "NOAA 19" in names


def test_update_satellites_replaces_cache(tracker, sample_tle_list):
    tracker.update_satellites(sample_tle_list)
    assert len(tracker.get_satellite_objects()) == 2

    tracker.update_satellites([sample_tle_list[0]])
    assert len(tracker.get_satellite_objects()) == 1


def test_get_satellite_objects_empty(tracker):
    assert tracker.get_satellite_objects() == []
