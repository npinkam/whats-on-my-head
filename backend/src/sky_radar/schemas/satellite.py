from datetime import datetime

from pydantic import BaseModel


class SatellitePosition(BaseModel):
    name: str
    latitude: float
    longitude: float
    altitude_deg: float
    azimuth_deg: float
    range_km: float
    is_visible: bool


class SatelliteUpsertData(BaseModel):
    norad_cat_id: int
    name: str
    tle_line1: str
    tle_line2: str
    epoch: datetime
