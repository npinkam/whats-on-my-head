from fastapi import APIRouter, Query, Request

from sky_radar.api.exceptions import SatelliteNotFoundError
from sky_radar.services.tracker import SatelliteTracker

router = APIRouter()


@router.get("/api/satellites/{name}/trajectory")
async def get_trajectory(
    request: Request,
    name: str,
    steps: int = Query(default=200, ge=10, le=1000),
):
    tracker: SatelliteTracker = request.app.state.tracker

    # O(1) in-memory lookup — no DB query needed
    sat_data = tracker.get_satellite_data_by_name(name)
    if not sat_data:
        raise SatelliteNotFoundError(name)

    positions = tracker.calculate_trajectory(
        tle_line1=sat_data["tle_line1"],
        tle_line2=sat_data["tle_line2"],
        steps=steps,
    )

    return {"name": name, "trajectory": positions}
