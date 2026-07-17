from fastapi import APIRouter, Query, Request

from sky_radar.api.exceptions import SatelliteNotFoundError
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.tracker import SatelliteTracker

router = APIRouter()


@router.get("/api/satellites/{name}/trajectory")
async def get_trajectory(
    request: Request,
    name: str,
    steps: int = Query(default=200, ge=10, le=1000),
):
    tracker: SatelliteTracker = request.app.state.tracker
    repository = SatelliteRepository()

    async with request.app.state.db_session() as session:
        satellites = await repository.get_all_serialized(session)

    sat_data = next((s for s in satellites if s["name"] == name), None)
    if not sat_data:
        raise SatelliteNotFoundError(name)

    positions = tracker.calculate_trajectory(
        tle_line1=sat_data["tle_line1"],
        tle_line2=sat_data["tle_line2"],
        steps=steps,
    )

    return {"name": name, "trajectory": positions}
