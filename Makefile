.PHONY: help infra infra-down backend frontend dev dev-stop test test-backend test-frontend validate lint lint-backend lint-frontend typecheck format migrate migrate-create migrate-down clean

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Infrastructure ──────────────────────────────────────────────────────────

infra: ## Start PostgreSQL and Redis
	docker compose -f docker/docker-compose.infra.yml up -d

infra-down: ## Stop infrastructure
	docker compose -f docker/docker-compose.infra.yml down

# ─── Development Servers ─────────────────────────────────────────────────────

backend: ## Start backend dev server
	cd backend && uv run uvicorn sky_radar.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Start frontend dev server
	cd frontend && pnpm dev

dev: infra backend frontend ## Start full dev stack (infra + backend + frontend)

dev-stop: ## Stop all dev services
	docker compose -f docker/docker-compose.infra.yml down
	@echo "Note: Stop backend/frontend manually if running in separate terminals"

# ─── Testing ─────────────────────────────────────────────────────────────────

test: ## Run all tests (backend + frontend)
	cd backend && PATH="$$HOME/.local/bin:$$PATH" uv run pytest
	cd frontend && PATH="$$HOME/.local/share/pnpm/bin:$$HOME/.local/bin:$$PATH" pnpm vitest run

test-backend: ## Run backend tests only
	cd backend && uv run pytest

test-frontend: ## Run frontend tests only
	cd frontend && pnpm test

validate: ## Run all unit tests (backend + frontend) — gate before calling done
	$(MAKE) test

# ─── Linting ─────────────────────────────────────────────────────────────────

lint: ## Run all linters
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint

lint-backend: ## Run backend linter only
	cd backend && uv run ruff check . && uv run ruff format --check .

lint-frontend: ## Run frontend linter only
	cd frontend && pnpm lint

# ─── Type Checking ───────────────────────────────────────────────────────────

typecheck: ## Run all type checkers
	cd backend && uv run ty check src/
	cd frontend && pnpm typecheck

# ─── Formatting ──────────────────────────────────────────────────────────────

format: ## Format all code
	cd backend && uv run ruff format .
	cd frontend && pnpm lint --fix

# ─── Database ────────────────────────────────────────────────────────────────

migrate: ## Apply database migrations
	cd backend && uv run alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	cd backend && uv run alembic downgrade -1

# ─── Docker ──────────────────────────────────────────────────────────────────

full-stack: ## Start full stack via Docker (rebuild images)
	docker compose -f docker/docker-compose.full.yml up -d --build

full-stack-down: ## Stop full stack
	docker compose -f docker/docker-compose.full.yml down

# ─── Utility ─────────────────────────────────────────────────────────────────

precommit-setup: ## Configure git to use .githooks/pre-commit
	git config core.hooksPath .githooks

clean: ## Clean build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".ty_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name ".nuxt" -exec rm -rf {} +
	find . -type d -name ".output" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
