# T3.2 — production image for the dMRV backend.
# Slim, pinned, non-root. Migrations run at startup via the FastAPI lifespan
# (init_db) unless DMRV_SKIP_MIGRATIONS=1.
FROM python:3.11-slim

# curl is used by the container HEALTHCHECK below; keep the layer minimal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for layer caching.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY backend/ .

# Drop privileges — the process never needs root.
RUN useradd -r -u 10001 dmrv && chown -R dmrv /app
USER dmrv

EXPOSE 8001

# /api/health is a real DB probe (T2.6) — a healthy container means the DB is reachable.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8001/api/health || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
