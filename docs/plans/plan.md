# SkyRadar Implementation Plan

## Phase 1: Foundation

### 1.1 Backend Scaffold
- [x] `pyproject.toml` with uv, FastAPI, Skyfield, SQLAlchemy 2.0, asyncpg, pydantic-settings, loguru, ruff
- [x] `.python-version` pinning 3.12
- [x] `alembic.ini` + `migrations/env.py` for async Alembic
- [x] `src/sky_radar/config.py` — Pydantic BaseSettings loading DATABASE_URL, REDIS_URL, CORS_ORIGINS, LOG_LEVEL
- [x] `src/sky_radar/main.py` — FastAPI app with Lifespan handler (init DB engine, Redis pool, Skyfield loader)
- [x] `src/sky_radar/logging.py` — Loguru structured JSON config

### 1.2 Infrastructure
- [x] `docker-compose.yml` — PostgreSQL 16, Redis 7, with health checks
- [x] `.env.example` — All required env vars documented
- [x] `.gitignore` — Python, Node, env, IDE, build artifacts

### 1.3 Frontend Scaffold
- [x] `nuxt.config.ts` — API proxy, Tailwind module, TypeScript strict mode
- [x] `package.json` — Nuxt 3, Leaflet, Tailwind, Vitest, Playwright
- [x] `tailwind.config.js` — Content paths
- [x] `app.vue` — Skeleton layout with map container

## Phase 2: Data Layer

### 2.1 Database Models
- [x] `models.py` — SQLAlchemy 2.0 declarative `Satellite` model (id, name, tle_line1, tle_line2, epoch, updated_at)
- [x] Alembic initial migration
- [x] `repository.py` — Async bulk upsert using `insert().on_conflict_do_update()`

### 2.2 CelesTrak Client
- [x] `client.py` — httpx async client fetching TLE groups
- [x] Retry logic with exponential backoff
- [x] Response parsing into (name, line1, line2) tuples

### 2.3 Redis Cache Layer
- [x] Distributed lock via `redis.SET NX EX` for sync coordination
- [x] TLE cache: serialized JSON of satellite catalog with TTL
- [x] Connection pool management in Lifespan
- [x] `cache.py` — Redis cache with lock acquisition/release and TLE caching

## Phase 3: Orbital Computation

### 3.1 Skyfield Integration
- [x] `tracker.py` — Load TLE into Skyfield `EarthSatellite` objects
- [x] Observer-relative position calculation (azimuth, elevation, range)
- [x] Sub-satellite point (lat/lon) projection onto WGS84
- [x] Ephemeris download handler (de421.bsp)

### 3.2 Computation Pipeline
- [x] Batch propagation for all cached satellites
- [x] Filter by visibility (elevation > 0 for overhead pass)
- [x] Serialize results for WebSocket broadcast

## Phase 4: Real-Time Streaming

### 4.1 WebSocket Handler
- [x] `/ws` endpoint in `main.py`
- [x] Connection manager tracking active clients
- [x] 1Hz broadcast loop: propagate → serialize → send JSON
- [x] Client location input (lat/lon) for observer-relative calculations
- [x] Graceful disconnect handling

### 4.2 Background Sync
- [x] FastAPI background task or lifespan-spawned coroutine
- [x] 12-hour TLE refresh cycle
- [x] Lock acquisition → fetch → upsert → cache update
- [x] Error handling and retry on failure

## Phase 5: Frontend

### 5.1 Map Component
- [x] Leaflet map initialization with OpenStreetMap tiles
- [x] Satellite markers with lat/lon from WebSocket data
- [x] Auto-center on user location
- [x] Satellite detail popup (name, elevation, range, velocity)

### 5.2 Dashboard UI
- [x] Location input form (lat/lon or geolocation API)
- [x] Connection status indicator (WebSocket state)
- [x] Satellite count and overhead pass list
- [x] Tailwind responsive layout

### 5.3 WebSocket Client
- [x] Composable for WebSocket connection management
- [x] Auto-reconnect with backoff
- [x] Reactive satellite position updates
- [x] Send observer location to backend

## Phase 5.5: Backend Package Restructure

Current flat structure in `src/sky_radar/` needs reorganization for scalability.

### Current Issues Identified
| Issue | Location | Severity |
|-------|----------|----------|
| **God `main.py`** — routes, business logic, background tasks, lifespan all in one 162-line file | `main.py` | High |
| **No Pydantic schemas** — API responses are raw dicts, no validation | `tracker.py`, `main.py` | High |
| **Module-level singletons** — `cache` and `manager` instantiated at import time, untestable | `cache.py`, `websocket.py` | High |
| **Deprecated `@app.on_event("startup")`** — should use lifespan context manager | `main.py` | Medium |
| **`datetime.utcnow()` deprecated** in Python 3.12 | `main.py`, `cache.py`, `tracker.py` | Medium |
| **`setup_logging()` never called** — function exists but is dead code | `logging.py` | Medium |
| **SQLAlchemy 1.x style** — `Column()` instead of 2.0 `Mapped[]`/`mapped_column()` | `models.py` | Low |
| **No dependency injection** — `app.state` as service locator instead of `Depends` | `main.py` | Medium |
| **Repository is free functions** — no abstraction, hard to mock/swap | `repository.py` | Medium |
| **Broadcast loop recreates `EarthSatellite` objects every tick** per client | `main.py` | Medium (perf) |

### Target Structure
```
src/sky_radar/
├── __init__.py                     # Package root (minimal)
├── main.py                         # App factory + lifespan ONLY
├── config.py                       # Settings (unchanged)
├── logging.py                      # Loguru setup (unchanged, but actually called)
│
├── api/                            # HTTP/WS layer — thin, delegates to services
│   ├── __init__.py
│   ├── dependencies.py             # FastAPI Depends: get_db_session, get_cache, etc.
│   ├── health.py                   # GET /health, GET /ready
│   └── websocket.py                # WS /ws/{client_id}
│
├── models.py                       # SQLAlchemy ORM models (flat until >3 models)
│
├── schemas/                        # Pydantic request/response/message models
│   ├── __init__.py
│   ├── satellite.py                # SatelliteResponse, SatellitePosition
│   └── websocket.py                # WSMessage, ClientLocationUpdate
│
├── repositories/                   # Data access layer (classes, not free functions)
│   ├── __init__.py
│   └── satellite.py                # SatelliteRepository class
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── celestrak.py                # CelesTrakClient (moved from client.py)
│   ├── tracker.py                  # SatelliteTracker (moved from tracker.py)
│   ├── tle_sync.py                 # TLE sync orchestration (extracted from main.py)
│   └── broadcaster.py              # Position broadcast loop (extracted from main.py)
│
└── infrastructure/                 # External system adapters
    ├── __init__.py
    ├── cache.py                    # RedisCache (moved from cache.py)
    └── websocket_manager.py        # ConnectionManager (moved from websocket.py)
```

### Migration Steps
#### Phase 1: Extract schemas (no behavior change)
- [x] Create `schemas/` package with `satellite.py` and `websocket.py`
- [x] Define `SatellitePosition`, `SatelliteListResponse`, `WSPositionMessage`, `ClientLocationUpdate` as Pydantic models
- [x] Update `tracker.py:serialize_for_websocket` to return `WSPositionMessage`
- [x] Update `main.py` health endpoints to use response models
- [x] **Verify:** `ruff check . && ty src/ && pytest`

#### Phase 2: Extract services from `main.py`
- [x] Create `services/tle_sync.py` — move `sync_tle_data()` into a `TLESyncService` class
- [x] Create `services/broadcaster.py` — move `broadcast_satellite_positions()` into a `BroadcasterService` class
- [x] `main.py` lifespan creates these services and stores them; startup task calls `broadcaster.run()`
- [x] **Verify:** `ruff check . && ty src/ && pytest`

#### Phase 3: Extract API routes
- [x] Create `api/` package
- [x] Move health/readiness to `api/health.py` as an `APIRouter`
- [x] Move WebSocket endpoint to `api/websocket.py` as an `APIRouter`
- [x] Create `api/dependencies.py` with `get_db_session()`, `get_cache()`, `get_tracker()` etc. using `Depends`
- [x] `main.py` becomes: create app → add middleware → include routers → lifespan
- [x] **Verify:** `ruff check . && ty src/ && pytest`

#### Phase 4: Refactor repositories and infrastructure
- [x] Convert `repository.py` free functions → `repositories/satellite.py` with `SatelliteRepository` class
- [x] Move `cache.py` → `infrastructure/cache.py` (remove module-level singleton, instantiate in lifespan)
- [x] Move `websocket.py` → `infrastructure/websocket_manager.py` (remove module-level singleton)
- [x] Rename `client.py` → `services/celestrak.py`
- [x] Update all imports
- [x] **Verify:** `ruff check . && ty src/ && pytest`

#### Phase 5: Fix deprecated APIs and code quality
- [x] Replace `datetime.utcnow()` → `datetime.now(tz=timezone.utc)` everywhere
- [x] Remove `@app.on_event("startup")` — move broadcast task creation into lifespan
- [x] Call `setup_logging()` at the start of lifespan
- [x] Convert `models.py` to SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column()`)
- [x] **Verify:** `ruff check . && ty src/ && pytest`

### Additional Recommendations
- [x] **Dependency injection over singletons**: Replace module-level `cache = RedisCache(...)` and `manager = ConnectionManager()` with lifespan-scoped instances passed via FastAPI `Depends`
- [x] **Performance**: Cache `EarthSatellite` objects and only rebuild when TLE data changes
- [x] **Error handling**: Add custom exception classes and register FastAPI exception handlers
- [x] **Structured logging**: Add JSON output for production
- [x] **Type safety**: `bulk_upsert_satellites` should take `list[SatelliteUpsertData]` instead of `list[dict]`
- [x] **Testing**: Add `pytest-httpx` for mocking httpx, `fakeredis` for integration-testing `RedisCache`

### Benefits
- Clear separation of concerns (API / Models / Repos / Services / Infrastructure)
- Easier to add new features without cluttering root
- Follows standard FastAPI project patterns
- Scales well as project grows
- Testable (no global singletons)
- Type-safe (Pydantic schemas for all API boundaries)

## Phase 6: Testing & Quality

### 6.1 Backend Tests
- [x] `conftest.py` — Async DB session fixture, mock Redis, TestClient
- [x] Unit tests for `tracker.py` (known satellite positions)
- [x] Unit tests for `repository.py` (upsert logic)
- [x] Integration tests for API endpoints
- [x] WebSocket connection test

### 6.2 Frontend Tests
- [x] Vitest unit tests for composables
- [ ] Playwright E2E: connect, enter location, see satellites on map

### 6.3 CI Pipeline
- [x] `.github/workflows/ci.yml` — lint, typecheck, test, build
- [x] Backend: ruff → ty → pytest
- [x] Frontend: eslint → typecheck → vitest → build

## Phase 7: Hardening

- [x] Health check endpoints (`/health`, `/ready`)
- [x] CORS configuration
- [x] Rate limiting via Redis
- [x] Structured error responses
- [x] Loguru JSON logging for production
- [x] Dockerfiles for backend and frontend
- [x] Production docker-compose override
