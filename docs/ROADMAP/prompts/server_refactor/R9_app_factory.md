# R9 — Extract `app_factory.py` (application assembly)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 9 of 10. R1–R8 must be committed & green. Pure relocation.
> Baseline gate: **416 passed, 2 skipped**. ONE commit. Do not start R10.

**What moves:** the FastAPI application construction — `lifespan`, `app = FastAPI(...)`, CORS setup,
`_ALLOWED_ORIGIN`, `UPLOAD_DIR`, middleware registration, router includes, and the portal mount.

After R8, server.py should contain roughly:
- Import block (stdlib + facade re-exports)
- `lifespan` context manager
- `app = FastAPI(...)` construction
- `_ALLOWED_ORIGIN` + CORS middleware setup
- `_MAX_JSON_BODY_BYTES`, `_MAX_MEDIA_BODY_BYTES` (if not moved in R8)
- Middleware registration (`app.middleware(...)`)
- `observability.install_middleware(app)`
- `UPLOAD_DIR`
- Router includes (from R8)
- Portal router mount

All of this becomes `app_factory.py`.

---

## STEP 1 — Create `backend/app_factory.py`

```python
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
```

> **IMPORTANT — `UPLOAD_DIR` placement:** `UPLOAD_DIR` is used by `routers/media.py` and by the portal
> media download. It must be importable. Place it in `app_factory.py` (alongside the app) and have
> `routers/media.py` do `from app_factory import UPLOAD_DIR`. Alternatively, place it in `settings.py`
> if that's cleaner — pick one, be consistent.

> **IMPORTANT — `_ALLOWED_ORIGIN`:** This was a module-level constant in server.py. In `create_app()` it
> becomes a local variable, which is fine — it's only used during construction.

---

## STEP 2 — Edit `backend/server.py`

1. **Delete** from server.py:
   - `lifespan` (~line 321)
   - `app = FastAPI(...)` construction (~line 327)
   - `_ALLOWED_ORIGIN` (~line 335)
   - The entire CORS `app.add_middleware(...)` block (~lines 337–354)
   - `UPLOAD_DIR` (~line 502)
   - All `@app.middleware("http")` registrations
   - `observability.install_middleware(app)` (~line 498)
   - All `app.include_router(...)` calls
   - The `from portal.routes import router as portal_router` (~line 2760)

2. **Replace with a single import at the top:**
   ```python
   from app_factory import app, create_app, lifespan, UPLOAD_DIR  # noqa: F401  (R9 facade)
   ```
   
   Also re-export `_ALLOWED_ORIGIN` if any test references it:
   ```
   grep -rn "_ALLOWED_ORIGIN" backend/tests/
   ```
   If referenced, add: `_ALLOWED_ORIGIN = os.environ.get("DMRV_ALLOWED_ORIGIN", "")`

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import app, UPLOAD_DIR; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
   - Watch: `test_p1_24_cors.py` (exercises CORS setup), `test_rate_limit.py` (middleware order),
     any test that imports `UPLOAD_DIR` from server.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R9** — extracted app_factory.py (create_app + assembly); server.py ~250→~60; 416/2 green`
- Commit:
  ```
  refactor(backend): extract app_factory.py — server.py ~250→~60 LOC (P4.8/R9)

  Pure relocation, no behavior change. App construction, CORS, middleware
  registration, and router includes in a single composition root.
  Suite green (416 passed, 2 skipped). Facade re-exports preserve import surface.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
