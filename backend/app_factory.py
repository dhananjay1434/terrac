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
    # V8 Part 0.4/0.1: if server signing is configured, fail fast at boot when
    # the private key doesn't match the published pubkey for its kid. Otherwise
    # the /api/v1/config endpoint would happily sign documents that NO device
    # can verify — the app treats an unverifiable config as "none", so the
    # kill-switch would silently do nothing in an emergency with no server-side
    # error. Guarded on all three env vars being present so a deployment that
    # doesn't use signing is never forced to configure it.
    if (
        os.environ.get("DMRV_SERVER_SIGNING_SK")
        and os.environ.get("DMRV_SERVER_SIGNING_KID")
        and os.environ.get("DMRV_SERVER_SIGNING_PUBKEYS")
    ):
        import server_signing

        server_signing.validate_consistency()  # raises on any mismatch
        log.info("Server signing key validated")
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
    from routers.exports import router as exports_router
    from routers.config import router as config_router
    from routers.farmers import router as farmers_router
    from routers.dispatch import router as dispatch_router
    from routers.field_walk import router as field_walk_router

    application.include_router(health_router)
    application.include_router(devices_router)
    application.include_router(batches_router)
    application.include_router(evidence_router)
    application.include_router(media_router)
    application.include_router(lab_router)
    application.include_router(admin_router)
    application.include_router(compliance_router)
    application.include_router(exports_router)
    application.include_router(config_router)
    application.include_router(farmers_router)
    application.include_router(dispatch_router)
    application.include_router(field_walk_router)

    # Portal
    from portal.routes import router as portal_router

    application.include_router(portal_router)

    return application


# Media upload directory — relative to this file, works on Windows + Linux + Docker.
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Module-level app for backwards compat (uvicorn points to server:app or app_factory:app)
app = create_app()
