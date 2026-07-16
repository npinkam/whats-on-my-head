from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.client_ids: dict[int, str] = {}
        self.client_locations: dict[str, tuple[float, float]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.client_ids[id(websocket)] = client_id
        self.active_connections.append(websocket)
        self.client_locations[client_id] = (0.0, 0.0)
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_ids.pop(id(websocket), None)
        if client_id in self.client_locations:
            del self.client_locations[client_id]
        logger.info(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")

    def get_client_id(self, websocket: WebSocket) -> str:
        return self.client_ids.get(id(websocket), "")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    def update_client_location(self, client_id: str, latitude: float, longitude: float):
        self.client_locations[client_id] = (latitude, longitude)
        logger.debug(f"Client {client_id} location updated: {latitude}, {longitude}")

    def get_client_location(self, client_id: str) -> tuple[float, float]:
        return self.client_locations.get(client_id, (0.0, 0.0))
