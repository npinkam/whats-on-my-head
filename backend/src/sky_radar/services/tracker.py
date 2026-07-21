import math
from datetime import UTC, datetime, timedelta

from loguru import logger
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.timelib import Time
from skyfield.toposlib import GeographicPosition

# Satellites closer than this many km to the observer might be visible.
# A satellite at ~2000 km altitude is visible up to ~5000 km ground distance.
# We use 6000 km as a generous pre-filter threshold.
_MAX_VISIBLE_GROUND_RANGE_KM = 6000.0


class SatelliteTracker:
    def __init__(self):
        self.ts = load.timescale()
        self.ephemeris = load("de421.bsp")
        self._satellite_cache: dict[str, EarthSatellite] = {}
        self._satellite_data_by_name: dict[str, dict] = {}

    def update_satellites(self, satellites_data: list[dict]) -> None:
        self._satellite_cache = {}
        self._satellite_data_by_name = {}
        for sat in satellites_data:
            name = sat["name"] if isinstance(sat, dict) else sat.name
            line1 = sat["tle_line1"] if isinstance(sat, dict) else sat.tle_line1
            line2 = sat["tle_line2"] if isinstance(sat, dict) else sat.tle_line2
            key = str(sat["norad_cat_id"]) if isinstance(sat, dict) else str(sat.norad_cat_id)
            self._satellite_cache[key] = EarthSatellite(line1, line2, name, self.ts)
            self._satellite_data_by_name[name] = {
                "norad_cat_id": sat["norad_cat_id"] if isinstance(sat, dict) else sat.norad_cat_id,
                "name": name,
                "tle_line1": line1,
                "tle_line2": line2,
            }

    def get_satellite_objects(self) -> list[EarthSatellite]:
        return list(self._satellite_cache.values())

    def get_satellite_data_by_name(self, name: str) -> dict | None:
        """Return raw TLE data for a satellite by name (in-memory, O(1))."""
        return self._satellite_data_by_name.get(name)

    def create_satellite(self, name: str, tle_line1: str, tle_line2: str) -> EarthSatellite:
        return EarthSatellite(tle_line1, tle_line2, name, self.ts)

    # ------------------------------------------------------------------
    # Public API (existing signatures preserved for backward compat)
    # ------------------------------------------------------------------

    def calculate_position(
        self,
        satellite: EarthSatellite,
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
    ) -> dict:
        """Calculate position of a single satellite relative to an observer."""
        if dt is None:
            dt = datetime.now(tz=UTC)

        t = self.ts.from_datetime(dt)
        observer = wgs84.latlon(latitude, longitude, elevation_m)
        return self._calculate_position_precomputed(satellite, observer, t)

    def calculate_trajectory(
        self,
        tle_line1: str,
        tle_line2: str,
        steps: int = 100,
    ) -> list[dict]:
        satellite = EarthSatellite(tle_line1, tle_line2, "", self.ts)

        mean_motion = float(tle_line2[52:63].strip())
        period = timedelta(minutes=1440.0 / mean_motion)
        half = period / 2

        now = datetime.now(tz=UTC)

        positions = []
        for i in range(steps):
            dt = now - half + (period * i / (steps - 1))
            t = self.ts.from_datetime(dt)
            subpoint = wgs84.subpoint_of(satellite.at(t))
            positions.append(
                {
                    "latitude": round(subpoint.latitude.degrees, 4),
                    "longitude": round(subpoint.longitude.degrees, 4),
                }
            )

        return positions

    def calculate_positions_batch(
        self,
        satellites: list[EarthSatellite],
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
        only_visible: bool = False,
    ) -> list[dict]:
        """Legacy batch method — delegates to the optimized path."""
        return self.calculate_positions_fast(
            satellites, latitude, longitude, elevation_m, dt, only_visible
        )

    # ------------------------------------------------------------------
    # Optimized path
    # ------------------------------------------------------------------

    def calculate_positions_fast(
        self,
        satellites: list[EarthSatellite],
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
        only_visible: bool = False,
    ) -> list[dict]:
        """
        Optimised batch: builds observer and time once, cheap pre-filter
        before the expensive altaz() call.  Subpoint reused — only one
        satellite.at(t) call per satellite.
        """
        if dt is None:
            dt = datetime.now(tz=UTC)

        t = self.ts.from_datetime(dt)
        observer = wgs84.latlon(latitude, longitude, elevation_m)

        positions: list[dict] = []
        for sat in satellites:
            try:
                subpoint = wgs84.subpoint_of(sat.at(t))

                if only_visible and not self._might_be_visible(sat, observer, t, subpoint=subpoint):
                    continue

                pos = self._calculate_position_from_subpoint(sat, observer, t, subpoint)

                if only_visible and not pos["is_visible"]:
                    continue

                positions.append(pos)
            except Exception as e:
                logger.warning(f"Failed to calculate position for {sat.name}: {e}")
                continue

        return positions

    def calculate_subpoints_batch(
        self,
        satellites: list[EarthSatellite],
        dt: datetime | None = None,
    ) -> list[dict]:
        """Compute Earth subpoints for all satellites at a given time.
        Observer-independent — call once and share across all clients."""
        if dt is None:
            dt = datetime.now(tz=UTC)

        t = self.ts.from_datetime(dt)

        results: list[dict] = []
        for sat in satellites:
            try:
                subpoint = wgs84.subpoint_of(sat.at(t))
                results.append(
                    {
                        "name": sat.name,
                        "latitude": subpoint.latitude.degrees,
                        "longitude": subpoint.longitude.degrees,
                        "elevation_km": subpoint.elevation.km,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed subpoint for {sat.name}: {e}")
                continue
        return results

    def filter_visible_from_subpoints(
        self,
        satellites: list[EarthSatellite],
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
        dt: datetime | None = None,
    ) -> list[dict]:
        """
        For each satellite compute the full observer-relative position
        ONLY if the pre-filter passes.  Each satellite's subpoint is
        computed once and reused for both the pre-filter and the position
        calculation — no double at(t) calls.
        """
        if dt is None:
            dt = datetime.now(tz=UTC)

        t = self.ts.from_datetime(dt)
        observer = wgs84.latlon(latitude, longitude, elevation_m)

        positions: list[dict] = []
        for sat in satellites:
            try:
                # Compute subpoint once — used by both pre-filter and position calc
                subpoint = wgs84.subpoint_of(sat.at(t))

                if not self._might_be_visible(sat, observer, t, subpoint=subpoint):
                    continue

                pos = self._calculate_position_from_subpoint(sat, observer, t, subpoint)
                if pos["is_visible"]:
                    positions.append(pos)
            except Exception as e:
                logger.warning(f"Failed visible-filter for {sat.name}: {e}")
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calculate_position_precomputed(
        self,
        satellite: EarthSatellite,
        observer: GeographicPosition,
        t: Time,
    ) -> dict:
        """Core position calc.  Caller provides pre-created observer + time."""
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

    @staticmethod
    def _might_be_visible(
        satellite: EarthSatellite,
        observer: GeographicPosition,
        t: Time,
        subpoint: GeographicPosition | None = None,
    ) -> bool:
        """
        Quick great-circle pre-check: if the satellite's subpoint is more
        than _MAX_VISIBLE_GROUND_RANGE_KM from the observer, it cannot be
        above the horizon.  Avoids the costly altaz() for ~75 % of the
        catalog (satellites on the other side of Earth).

        Uses the haversine formula for ground distance.

        If *subpoint* is provided (from a prior satellite.at(t) call),
        the internal at(t) call is skipped.
        """
        if subpoint is None:
            subpoint = wgs84.subpoint_of(satellite.at(t))

        lat1 = math.radians(observer.latitude.degrees)
        lon1 = math.radians(observer.longitude.degrees)
        lat2 = math.radians(subpoint.latitude.degrees)
        lon2 = math.radians(subpoint.longitude.degrees)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        central_angle = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Earth mean radius (km)
        ground_distance_km = 6371.0 * central_angle

        return ground_distance_km <= _MAX_VISIBLE_GROUND_RANGE_KM

    def _calculate_position_from_subpoint(
        self,
        satellite: EarthSatellite,
        observer: GeographicPosition,
        t: Time,
        subpoint: GeographicPosition,
    ) -> dict:
        """
        Core position calc using a pre-computed subpoint — avoids a
        second satellite.at(t) call in the hot path.
        """
        difference = satellite - observer
        topocentric = difference.at(t)

        alt, az, distance = topocentric.altaz()

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
