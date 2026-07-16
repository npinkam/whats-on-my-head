import asyncio

from loguru import logger

from sky_radar.infrastructure.websocket_manager import ConnectionManager
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.tracker import SatelliteTracker


class BroadcasterService:
    def __init__(
        self,
        tracker: SatelliteTracker,
        manager: ConnectionManager,
        repository: SatelliteRepository,
    ):
        self.tracker = tracker
        self.manager = manager
        self.repository = repository

    async def run(self, session_factory):
        while True:
            try:
                if not self.manager.active_connections:
                    await asyncio.sleep(1)
                    continue

                for websocket in self.manager.active_connections:
                    client_id = self.manager.get_client_id(websocket)
                    lat, lon = self.manager.get_client_location(client_id)
                    if lat == 0.0 and lon == 0.0:
                        continue

                    sat_objects = self.tracker.get_satellite_objects()

                    positions = self.tracker.calculate_positions_batch(
                        sat_objects, lat, lon, only_visible=True
                    )

                    message = self.tracker.serialize_for_websocket(positions)
                    await self.manager.send_personal_message(message, websocket)

            except Exception as e:
                logger.error(f"Broadcast error: {e}")

            await asyncio.sleep(1)
