# SkyRadar: What's on My Head?

Real-time satellite visualizer for the **full active satellite catalog** (15,000+ objects). Tracks overhead objects using TLE data from [CelesTrak](https://celestrak.org), propagated via [Skyfield](https://github.com/skyfielders/python-skyfield), and streamed to a browser-based Leaflet map over WebSockets.

**Data pipeline:** CelesTrak → Redis distributed lock → Background sync worker → PostgreSQL (upsert) + Redis cache → WebSocket stream (3s interval) → Client browser.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, Skyfield, SQLAlchemy 2.0, asyncpg |
| State | Redis (distributed lock + TLE cache + rate limiter) |
| Database | PostgreSQL 16 |
| Frontend | Nuxt 3, Vue 3.5+, Leaflet.js, Tailwind CSS |
| Tooling | uv, Ruff, ty, pnpm, ESLint, Vitest |

## AI Stack

This project was built with AI-assisted development tools:

| Tool | Purpose |
|------|---------|
| [OpenCode](https://opencode.ai) | AI coding agent in the terminal |
| [OpenRouter](https://openrouter.ai) | Unified API for multiple LLM providers |
| DeepSeek V4 Flash | Primary model for code generation |
| Qwen | Secondary model for reasoning and planning |

## Architecture

```
CelesTrak (every 12h)
    │
    ▼
Redis Distributed Lock (prevents thundering herd)
    │
    ▼
FastAPI TLE Sync Worker
    ├──► SatelliteRepository.bulk_upsert() → PostgreSQL
    ├──► RedisCache.cache_tle_data()       → Redis
    └──► SatelliteTracker.update_satellites() → Skyfield cache

Client Browser ◄── WebSocket (3s interval) ──► BroadcasterService
                                         ├── For each client (lat/lon)
                                         ├── Propagate all EarthSatellite objects
                                         └── Filter to visible (altitude > 0)
```

## Project Structure

```
├── backend/
│   ├── src/sky_radar/
│   │   ├── main.py                  # FastAPI app factory + lifespan
│   │   ├── config.py                # Pydantic BaseSettings
│   │   ├── models.py                # SQLAlchemy 2.0 ORM (Satellite)
│   │   ├── api/                     # HTTP/WS routes (thin, delegates to services)
│   │   │   ├── dependencies.py
│   │   │   ├── exceptions.py
│   │   │   ├── health.py            # GET /health, GET /ready
│   │   │   ├── satellites.py        # GET /api/satellites/search
│   │   │   └── websocket.py         # WS /ws/{client_id}
│   │   ├── infrastructure/
│   │   │   ├── cache.py             # RedisCache (lock + TLE cache)
│   │   │   ├── rate_limiter.py       # Redis-based rate limiter
│   │   │   └── websocket_manager.py  # ConnectionManager
│   │   ├── repositories/
│   │   │   └── satellite.py         # SatelliteRepository (bulk upsert)
│   │   ├── schemas/
│   │   │   ├── satellite.py         # Pydantic models
│   │   │   └── websocket.py         # WS message schemas
│   │   └── services/
│   │       ├── broadcaster.py       # 3s broadcast loop
│   │       ├── celestrak.py         # CelesTrak HTTP client (retry/backoff)
│   │       ├── tle_sync.py          # TLE sync orchestration
│   │       └── tracker.py           # Skyfield orbital propagation
│   ├── tests/
│   ├── migrations/                  # Alembic
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app.vue                      # Dashboard + map + WebSocket UI
│   ├── components/
│   │   ├── SatelliteMap.vue         # Leaflet map with satellite markers
│   │   └── SatelliteSearch.vue      # Satellite name search with dropdown
│   ├── composables/
│   │   └── useWebSocket.ts          # WebSocket composable
│   ├── tests/
│   ├── nuxt.config.ts
│   ├── nginx.conf                   # SPA + WS proxy to backend
│   ├── Dockerfile
│   └── vitest.config.ts
├── docker/
│   ├── docker-compose.infra.yml     # Postgres + Redis
│   ├── docker-compose.backend.yml   # Backend service
│   ├── docker-compose.frontend.yml  # Frontend service
│   └── docker-compose.full.yml      # Full stack
└── docs/plans/
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for Postgres + Redis)
- `uv` (package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd whats-on-my-head

# 2. Start infrastructure (Postgres + Redis)
make infra

# 3. Backend setup (separate terminal)
cd backend
uv sync
cp .env.example .env
make migrate
make backend          # starts on http://localhost:8000

# 4. Frontend setup (separate terminal)
cd frontend
pnpm install
make frontend         # starts on http://localhost:3000
```

Open `http://localhost:3000`, enter your latitude/longitude, and watch satellites fly overhead.

## Makefile Commands

```bash
# Infrastructure
make infra                    # Start PostgreSQL and Redis
make infra-down               # Stop infrastructure

# Development
make backend                  # Start backend dev server (:8000)
make frontend                 # Start frontend dev server (:3000)
make dev                      # Start dev stack: infra + backend + frontend
make dev-stop                 # Stop all dev services

# Testing
make test                     # Run all tests (backend + frontend)
make test-backend             # Run backend tests only
make test-frontend            # Run frontend tests only

# Linting
make lint                     # Run all linters
make lint-backend             # Run backend linter (Ruff)
make lint-frontend            # Run frontend linter (ESLint)

# Type Checking
make typecheck                # Run all type checkers

# Formatting
make format                   # Format all code

# Database
make migrate                  # Apply database migrations
make migrate-create MSG="desc"  # Create new migration
make migrate-down              # Rollback last migration
make schema-check              # Verify models are in sync with migrations

# Docker
make full-stack               # Start full stack via Docker (--build)
make full-stack-down          # Stop full stack

# Utility
make clean                    # Clean build artifacts and caches
```

### Docker Stacks

```bash
# Infrastructure only (recommended for local dev)
docker compose -f docker/docker-compose.infra.yml up -d

# Full stack (everything)
docker compose -f docker/docker-compose.full.yml up -d --build

# Individual services
docker compose -f docker/docker-compose.backend.yml up -d
docker compose -f docker/docker-compose.frontend.yml up -d
```

## APIs

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /ready` | Readiness check |
| `GET /api/satellites/search?q={query}` | Search satellites by name (case-insensitive) |
| `WS /ws/{client_id}` | WebSocket — send lat/lon, receive satellite positions every 3s |

### WebSocket Protocol

**Client → Server:**
```json
{"latitude": 40.7128, "longitude": -74.0060}
```

**Server → Client (3s interval):**
```json
{
  "type": "positions",
  "satellites": [
    {"name": "ISS (ZARYA)", "latitude": 51.4, "longitude": -120.2, "altitude": 408.0, "azimuth": 180.5, "elevation": 45.2}
  ]
}
```

## TLE Sync

The **full active catalog** (~15,000 satellites) is fetched from CelesTrak as a single bulk query on a 12-hour cycle. The raw response is saved to a local artifact file for fallback if CelesTrak is unreachable.

## Development

See [AGENTS.md](./AGENTS.md) for detailed commands, conventions, and verification steps.

### Verification Order

```
ruff check . → ruff format --check . → ty src/ → pytest
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/sky_radar` | Postgres DSN |
| `REDIS_URL` | `redis://localhost:6379` | Redis DSN |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Log level |
| `TLE_SYNC_INTERVAL_HOURS` | `12` | TLE sync frequency |
| `CELESTRAK_BASE_URL` | `https://celestrak.org` | CelesTrak API base URL |
