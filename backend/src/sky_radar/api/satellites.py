from fastapi import APIRouter, Query, Request

from sky_radar.services.tracker import SatelliteTracker

router = APIRouter()


@router.get("/api/satellites/search")
async def search_satellites(
    request: Request,
    q: str = Query(default="", min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
):
    tracker: SatelliteTracker = request.app.state.tracker

    query = q.lower().strip()
    results: list[dict] = []

    for name, data in tracker._satellite_data_by_name.items():
        if query in name.lower():
            results.append(
                {
                    "name": data["name"],
                    "norad_cat_id": data["norad_cat_id"],
                }
            )

    return {"query": q, "results": results[:limit]}
