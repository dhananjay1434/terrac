"""FastAPI application factory (extracted from server.py, R9).

Single composition root: creates the app, attaches CORS, registers middleware
in the correct order (SOP §6.4), and includes all domain routers + the portal.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import observability
from db import init_db
from settings import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("Database initialized")
    yield


def create_app() -> FastAPI:
    """Build and return the fully-assembled FastAPI application."""
    application = FastAPI(
        title="Kon-Tiki dMRV API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    allowed_origin = os.environ.get("DMRV_ALLOWED_ORIGIN", "")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin] if allowed_origin else [],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Device-Id",
            "X-Idempotency-Key",
            "X-Payload-Sha256",
            "X-Signature",
            "X-Enrollment-Token",
            "X-Admin-Secret",
        ],
    )

    # Middleware — ORDER MATTERS (SOP §6.4):
    # 1. _limit_body_size (registered first → outermost after CORS)
    # 2. _rate_limit (registered second → runs inside body-size)
    # 3. observability (registered last → actually outermost, wraps everything)
    from middleware import _limit_body_size, _rate_limit

    application.middleware("http")(_limit_body_size)
    application.middleware("http")(_rate_limit)
    observability.install_middleware(application)

    # Domain routers
    from routers.health import router as health_router
    from routers.devices import router as devices_router
    from routers.batches import router as batches_router
    from routers.evidence import router as evidence_router
    from routers.media import router as media_router
    from routers.lab import router as lab_router
    from routers.admin import router as admin_router
    from routers.compliance import router as compliance_router

    application.include_router(health_router)
    application.include_router(devices_router)
    application.include_router(batches_router)
    application.include_router(evidence_router)
    application.include_router(media_router)
    application.include_router(lab_router)
    application.include_router(admin_router)
    application.include_router(compliance_router)

    # Portal
    from portal.routes import router as portal_router

    application.include_router(portal_router)

    return application


# Media upload directory — relative to this file, works on Windows + Linux + Docker.
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Module-level app for backwards compat (uvicorn points to server:app or app_factory:app)
app = create_app()
