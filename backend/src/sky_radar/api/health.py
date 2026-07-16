from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from sky_radar.infrastructure.rate_limiter import RateLimiter

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    rate_limiter: RateLimiter = request.app.state.rate_limiter
    allowed = await rate_limiter.check_rate_limit(key="health", max_requests=30, window_seconds=60)
    if not allowed:
        return JSONResponse(status_code=429, content={"error": "rate_limited"})
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(request: Request):
    rate_limiter: RateLimiter = request.app.state.rate_limiter
    allowed = await rate_limiter.check_rate_limit(key="ready", max_requests=30, window_seconds=60)
    if not allowed:
        return JSONResponse(status_code=429, content={"error": "rate_limited"})
    return {"status": "ready"}
