from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from sky_radar.infrastructure.cache import RedisCache
from sky_radar.infrastructure.websocket_manager import ConnectionManager
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.celestrak import CelesTrakClient
from sky_radar.services.tracker import SatelliteTracker


def get_cache(request: Request) -> RedisCache:
    return request.app.state.cache


def get_manager(request: Request) -> ConnectionManager:
    return request.app.state.manager


def get_repository(request: Request) -> SatelliteRepository:
    return request.app.state.repository


def get_tracker(request: Request) -> SatelliteTracker:
    return request.app.state.tracker


def get_celes_trak_client(request: Request) -> CelesTrakClient:
    return request.app.state.celes_trak_client


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.db_session() as session:
        yield session
