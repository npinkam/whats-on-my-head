from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette import status

from sky_radar.infrastructure.rate_limiter import RateLimiter
from sky_radar.infrastructure.websocket_manager import ConnectionManager

router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    rate_limiter: RateLimiter = websocket.app.state.rate_limiter
    allowed = await rate_limiter.check_rate_limit(
        key=f"ws:{client_id}", max_requests=5, window_seconds=60
    )
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    manager: ConnectionManager = websocket.app.state.manager
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if "latitude" in data and "longitude" in data:
                manager.update_client_location(client_id, data["latitude"], data["longitude"])
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
