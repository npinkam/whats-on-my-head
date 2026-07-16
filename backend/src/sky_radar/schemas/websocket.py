from pydantic import BaseModel


class WSPositionMessage(BaseModel):
    timestamp: str
    observer: dict[str, float]
    satellites: list[dict]


class ClientLocationUpdate(BaseModel):
    latitude: float
    longitude: float
