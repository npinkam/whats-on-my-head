import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sky_radar.api.exceptions import CacheError, TLEFetchError
from sky_radar.api.health import router as health_router
from sky_radar.api.satellites import router as satellites_router
from sky_radar.api.trajectory import router as trajectory_router
from sky_radar.api.websocket import router as websocket_router
from sky_radar.config import settings
from sky_radar.infrastructure.cache import RedisCache
from sky_radar.infrastructure.rate_limiter import RateLimiter
from sky_radar.infrastructure.websocket_manager import ConnectionManager
from sky_radar.logging import setup_logging
from sky_radar.models import Base
from sky_radar.repositories.satellite import SatelliteRepository
from sky_radar.services.broadcaster import BroadcasterService
from sky_radar.services.celestrak import CelesTrakClient
from sky_radar.services.tle_sync import TLESyncService
from sky_radar.services.tracker import SatelliteTracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting SkyRadar backend")

    cache = RedisCache(settings.redis_url)
    await cache.connect()
    await cache.clear_stale_lock()

    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    manager = ConnectionManager()
    repository = SatelliteRepository()
    tracker = SatelliteTracker()
    client = CelesTrakClient(settings.celes_trak_base_url)

    rate_limiter = RateLimiter(cache)

    app.state.cache = cache
    app.state.db_engine = engine
    app.state.db_session = async_session
    app.state.manager = manager
    app.state.repository = repository
    app.state.tracker = tracker
    app.state.celes_trak_client = client
    app.state.rate_limiter = rate_limiter

    broadcaster = BroadcasterService(tracker, manager, repository)
    tle_sync = TLESyncService(client, cache, repository, tracker)

    async def run_tle_sync():
        await asyncio.sleep(2)
        async with async_session() as session:
            count = await tle_sync.sync(session)
            logger.info(f"Initial TLE sync completed: {count} satellites")

    async def periodic_tle_sync():
        while True:
            await asyncio.sleep(43200)
            try:
                async with async_session() as session:
                    await tle_sync.sync(session)
            except Exception as e:
                logger.error(f"Periodic TLE sync failed: {e}")

    asyncio.create_task(run_tle_sync())
    asyncio.create_task(periodic_tle_sync())
    asyncio.create_task(broadcaster.run(async_session))

    logger.info("Database engine and Redis cache initialized")

    yield

    logger.info("Shutting down SkyRadar backend")
    await client.close()
    await cache.disconnect()
    await engine.dispose()


app = FastAPI(
    title="SkyRadar API",
    description="Real-time satellite tracking and visualization",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(TLEFetchError)
async def tle_fetch_handler(request: Request, exc: TLEFetchError):
    return JSONResponse(status_code=502, content={"error": "tle_fetch_failed", "detail": str(exc)})


@app.exception_handler(CacheError)
async def cache_error_handler(request: Request, exc: CacheError):
    return JSONResponse(status_code=503, content={"error": "cache_error", "detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(satellites_router)
app.include_router(websocket_router)
app.include_router(trajectory_router)
