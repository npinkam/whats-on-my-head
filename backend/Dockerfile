# Stage 1: Build
FROM python:3.12-slim AS builder

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY src/ src/
RUN uv sync --no-dev --frozen

# Stage 2: Runtime
FROM python:3.12-slim

RUN groupadd -r skyradar && useradd -r -g skyradar -d /app -s /bin/false skyradar

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY --from=builder /app /app
RUN .venv/bin/python -c "from skyfield.api import load; load('de421.bsp')" && \
    chown -R skyradar:skyradar /app

EXPOSE 8000

USER skyradar

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD [".venv/bin/uvicorn", "sky_radar.main:app", "--host", "0.0.0.0", "--port", "8000"]