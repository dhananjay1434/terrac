# T3.2 — production image for the dMRV backend.
# Slim, pinned, non-root. Migrations run at startup via the FastAPI lifespan
# (init_db) unless DMRV_SKIP_MIGRATIONS=1.
#
# BUILD CONTEXT IS backend/  (P3.1): keep the context tiny and let
# backend/.dockerignore take effect — Docker reads .dockerignore from the
# context root, so a root context would both bloat the image with the Flutter
# tree and silently ignore backend/.dockerignore. Build with either
# `docker build backend` or compose's `build.context: ./backend`.
FROM python:3.11-slim

# curl is used by the container HEALTHCHECK below; keep the layer minimal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY . .

# Drop privileges — the process never needs root.
RUN useradd -r -u 10001 dmrv && chown -R dmrv /app
USER dmrv

EXPOSE 8001

# /api/health is a real DB probe (T2.6) — a healthy container means the DB is reachable.
# Honor $PORT so the same image runs on Render / Cloud Run (which inject it);
# default 8001 for docker-compose, local, and CI.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:${PORT:-8001}/api/health || exit 1

# --proxy-headers: Render terminates TLS and injects X-Forwarded-For; without
# this, request.client.host is the proxy IP and the per-IP rate limiter
# collapses to one global bucket. --forwarded-allow-ips='*' is safe here
# because the container is only reachable through Render's proxy.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers --forwarded-allow-ips='*'"]
