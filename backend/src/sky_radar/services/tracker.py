from datetime import UTC, datetime

from loguru import logger
from skyfield.api import EarthSatellite, load, wgs84


class SatelliteTracker:
    def __init__(self):
        self.ts = load.timescale()
        self.ephemeris = load("de421.bsp")
        self._satellite_cache: dict[str, EarthSatellite] = {}

    def update_satellites(self, satellites_data: list[dict]) -> None:
        self._satellite_cache = {}
        for sat in satellites_data:
            name = sat["name"] if isinstance(sat, dict) else sat.name
            line1 = sat["tle_line1"] if isinstance(sat, dict) else sat.tle_line1
            line2 = sat["tle_line2"] if isinstance(sat, dict) else sat.tle_line2
            self._satellite_cache[name] = EarthSatellite(line1, line2, name, self.ts)

    def get_satellite_objects(self) -> list[EarthSatellite]:
        return list(self._satellite_cache.values())

    def create_satellite(self, name: str, tle_line1: str, tle_line2: str) -> EarthSatellite:
        return EarthSatellite(tle_line1, tle_line2, name, self.ts)

    def calculate_position(
        self,
        satellite: EarthSatellite,
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
    ) -> dict:
        if dt is None:
            dt = datetime.now(tz=UTC)

        t = self.ts.from_datetime(dt)
        observer = wgs84.latlon(latitude, longitude, elevation_m)

        difference = satellite - observer
        topocentric = difference.at(t)

        alt, az, distance = topocentric.altaz()
        subpoint = wgs84.subpoint_of(satellite.at(t))

        return {
            "name": satellite.name,
            "latitude": subpoint.latitude.degrees,
            "longitude": subpoint.longitude.degrees,
            "elevation_km": subpoint.elevation.km,
            "altitude_deg": alt.degrees,
            "azimuth_deg": az.degrees,
            "range_km": distance.km,
            "is_visible": bool(alt.degrees > 0),
        }

    def calculate_positions_batch(
        self,
        satellites: list[EarthSatellite],
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
        only_visible: bool = False,
    ) -> list[dict]:
        positions = []
        for sat in satellites:
            try:
                pos = self.calculate_position(sat, latitude, longitude, elevation_m, dt)
                if only_visible and not pos["is_visible"]:
                    continue
                positions.append(pos)
            except Exception as e:
                logger.warning(f"Failed to calculate position for {sat.name}: {e}")
                continue
        return positions

    def serialize_for_websocket(self, positions: list[dict]) -> dict:
        return {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "observer": {
                "latitude": positions[0]["latitude"] if positions else 0.0,
                "longitude": positions[0]["longitude"] if positions else 0.0,
            },
            "satellites": [
                {
                    "name": pos["name"],
                    "latitude": pos["latitude"],
                    "longitude": pos["longitude"],
                    "altitude_deg": pos["altitude_deg"],
                    "azimuth_deg": pos["azimuth_deg"],
                    "range_km": pos["range_km"],
                    "is_visible": pos["is_visible"],
                }
                for pos in positions
            ],
        }
