# AGENTS.md

## Commands

```bash
# Quick commands (from project root)
make infra             # Start PostgreSQL and Redis
make backend           # Start backend dev server
make frontend          # Start frontend dev server
make test              # Run all tests (gate — run before calling done)
make lint              # Run all linters
make format            # Format code
make migrate           # Apply database migrations
make migrate-create MSG="description"  # Create new migration
make migrate-down      # Rollback last migration
make schema-check      # Verify models are in sync with migrations
make help              # Show all available commands

# Backend (from backend/)
uv sync                          # Install deps
uv run ruff check .              # Lint
uv run ruff format .             # Format
uv run ty src/                   # Typecheck
uv run pytest                    # All tests
uv run pytest tests/test_tracker.py::test_observer_position  # Single test
uv run alembic upgrade head      # Apply migrations
uv run alembic revision --autogenerate -m "description"  # New migration
uv run uvicorn sky_radar.main:app --reload  # Dev server

# Frontend (from frontend/)
pnpm install                     # Install deps
pnpm dev                         # Dev server
pnpm build                       # Production build
pnpm lint                        # ESLint
pnpm typecheck                   # Nuxt typecheck
pnpm test                        # Vitest
pnpm test:e2e                    # Playwright E2E
```

## Architecture

- **Backend**: FastAPI app in `backend/src/sky_radar/`. Entry point: `main.py`.
- **Frontend**: Nuxt 3 app in `frontend/`. Entry point: `app.vue`.
- **Pipeline**: CelesTrak → Redis lock → Background sync → Postgres upsert + Redis cache → WebSocket stream to clients.
- **Distributed lock**: Redis prevents thundering-herd on CelesTrak API. Cache holds serialized TLEs for ~1ms reads.
- **Orbital math**: Skyfield propagator in `services/tracker.py`. Computes observer-relative positions from TLE data.
- **DB**: SQLAlchemy 2.0 async models in `models.py`. Migrations via Alembic in `migrations/`.

### Backend Package Structure
```
src/sky_radar/
├── main.py              # App factory + lifespan
├── config.py            # Pydantic BaseSettings
├── logging.py           # Loguru configuration
├── models.py            # SQLAlchemy ORM models
├── api/                 # HTTP/WS routes (thin, delegates to services)
│   ├── dependencies.py  # FastAPI Depends functions
│   ├── health.py        # /health, /ready endpoints
│   ├── satellites.py    # GET /api/satellites/search
│   └── websocket.py     # WS /ws/{client_id}
├── schemas/             # Pydantic request/response models
├── repositories/        # Data access layer (class-based)
├── services/            # Business logic (celestrak, tracker, tle_sync, broadcaster)
└── infrastructure/      # External adapters (cache, websocket_manager)
```

## Conventions

- Python package layout: `src/sky_radar/` (src-layout).
- All DB access is async via `asyncpg`. Never use synchronous drivers.
- Pydantic v2 for all request/response schemas and config (`pydantic-settings`).
- Ruff for both linting and formatting. No Black/isort.
- Loguru for logging. No stdlib `logging`.
- WebSocket streams satellite positions to connected clients (default 3s interval).
- TLE sync runs on a 12-hour background cycle.

## Environment

Required services: PostgreSQL, Redis. Use `docker compose -f docker/docker-compose.infra.yml up -d` for local dev.
Skyfield ephemeris (`de421.bsp`) auto-downloads on first run (~30MB).

Docker stacks in `docker/`:
- `docker-compose.infra.yml` — Postgres + Redis (recommended for local dev)
- `docker-compose.backend.yml` — Backend service
- `docker-compose.frontend.yml` — Frontend service
- `docker-compose.full.yml` — Full stack (all services)

## Verification Order

`make test` — Hard gate. Run this before calling any implementation done.
