# R8 — Extract `middleware.py` + `routers/*.py` (21 route handlers)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 8 of 10. R1–R7 must be committed & green. Pure relocation.
> Baseline gate: **416 passed, 2 skipped**. ONE commit. Do not start R9.

**What moves:** all middleware functions, all route handlers, and the rate-limit infrastructure.
This is the biggest step by file count (1 + 8 new files), but each file is small and mechanical.

> **WARNING — SOP §6.4: Middleware order is behavioral.** The current registration order is:
> 1. `@app.middleware("http") _limit_body_size` (registered FIRST → outermost after CORS)
> 2. `@app.middleware("http") _rate_limit` (registered SECOND → runs inside body-size)
> 3. `observability.install_middleware(app)` (registered LAST → actually outermost, wraps everything)
>
> In R8 you move the middleware INTO `middleware.py` but DO NOT register them there. Registration stays
> in server.py (later moved to app_factory in R9). The middleware functions are plain `async def`s that
> take `(request, call_next)` — they are NOT decorated with `@app.middleware` in the new file.

---

## NEW FILES

### `backend/middleware.py`
Move from server.py:
1. `_MAX_JSON_BODY_BYTES = 2 * 1024 * 1024` (~line 360)
2. `_MAX_MEDIA_BODY_BYTES = 12 * 1024 * 1024` (~line 361)
3. `_limit_body_size` (~line 365) — **remove the `@app.middleware("http")` decorator**; it becomes a plain `async def`
4. `_RL_DEFAULT_CAPS` (~line 393)
5. `_RL_CAP_ENV` (~line 394)
6. `_rl_counters: dict = {}` (~line 402) — **MUTABLE DICT** (facade re-export = same object)
7. `_RL_MAX_COUNTERS = 4096` (~line 403)
8. `_rl_prune` (~line 406)
9. `_rl_int` → **DO NOT move if R2 already relocated it to settings.py.** If `_rl_int` is still in server.py (~line 427), move it here and import `env_int` from settings as the implementation. If R2 already moved it, import `_rl_int` from `settings` in middleware.py.
10. `_rl_enabled` (~line 434)
11. `_rl_window_seconds` (~line 438)
12. `_rl_now` (~line 442)
13. `_rl_bucket` (~line 447)
14. `_rate_limit` (~line 462) — **remove the `@app.middleware("http")` decorator**; plain `async def`

**Dependencies:**
- `os`, `time` (stdlib)
- `fastapi`: `Request`, `status`
- `fastapi.responses`: `JSONResponse`
- `settings` (after R2): `_rl_int` / `env_int`

> **Key constraint (SOP §6.5):** `_rl_enabled`, `_rl_window_seconds`, `_rl_int` read `os.environ` on every call.
> They MUST remain functions, not import-time constants.

### `backend/routers/__init__.py`
Empty file (makes `routers` a package).

### `backend/routers/health.py`
Move:
1. `health` route (~line 625, `GET /api/health`)
2. `metrics` route (~line 645, `GET /metrics`)

Dependencies: `datetime`, `timezone`, `select`, `func`, `AsyncSession`, `Depends`, `get_session`, `Batch`, `observability`, `JSONResponse`, `Header`, `Optional`, `status`

### `backend/routers/devices.py`
Move:
1. `register_device` (~line 801, `POST /api/v1/register`)
2. `mint_enrollment_token` (~line 859, `POST /api/v1/admin/mint-token`)

Dependencies: `datetime`, `timedelta`, `timezone`, `hmac`, `select`, `IntegrityError`, `AsyncSession`, `Depends`, `Header`, `HTTPException`, `status`, `Optional`, `get_session`, `DeviceKey`, `EnrollmentToken`, `RegistrationRequest`, `RegistrationResponse`, `MintTokenRequest` (from schemas after R4), `_ADMIN_SECRET` (from settings after R2), `attestation`

### `backend/routers/batches.py`
Move:
1. `create_batch` (~line 1794, **193 LOC**, `POST /api/v1/batches`)

Dependencies: `json`, `uuid`, `datetime`, `timezone`, `select`, `IntegrityError`, `AsyncSession`, `Depends`, `Header`, `HTTPException`, `Response`, `status`, `get_session`, `Batch`, `BatchPayload`, `BatchResponse` (from schemas), `verify_signature` (from security after R3), `recompute_batch_credit` (from credit_engine after R5), `get_storage` (from storage), `observability`, `log` (from settings)

### `backend/routers/evidence.py`
Move (7 routes):
1. `create_moisture` (~line 2307, `POST /api/v1/moisture`)
2. `create_composite_sample` (~line 2330, `POST /api/v1/composite-sample`)
3. `create_transport_event` (~line 2353, `POST /api/v1/transport-event`)
4. `create_telemetry` (~line 2377, `POST /api/v1/telemetry`)
5. `create_yield` (~line 2406, `POST /api/v1/yield`)
6. `create_metadata` (~line 2435, `POST /api/v1/metadata`)
7. `create_application` (~line 2465, `POST /api/v1/application`)

Dependencies: `json`, `select`, `IntegrityError`, `AsyncSession`, `Depends`, `HTTPException`, `status`, `get_session`, `MoistureReading`, `CompositePileSample`, `TransportEvent`, `PyrolysisTelemetry`, `YieldMetrics`, `SystemMetadata`, `EndUseApplication`, all evidence payload schemas (from schemas), `verify_signature` (from security), `_assert_batch_ownership`, `_upsert_one_to_one_evidence`, `_recompute_if_batch_exists`, `_assert_same_uuid` (from services.evidence after R6)

### `backend/routers/media.py`
Move:
1. `upload_media` (~line 1987, **163 LOC**, `POST /api/v1/media`)

Dependencies: `hashlib`, `uuid`, `select`, `AsyncSession`, `Depends`, `File`, `Header`, `HTTPException`, `UploadFile`, `status`, `Optional`, `get_session`, `Batch`, `MediaFile`, `MediaUploadResponse` (from schemas), `verify_media_signature` (from security), `_evaluate_anchor`, `_parse_exif_gps` (from geo after R1), `_SAFE` (from security after R3), `get_storage` (from storage), `UPLOAD_DIR` (stays in server.py until R9, import from server for now), `log` (from settings)

### `backend/routers/lab.py`
Move:
1. `ingest_lab_hcorg` (~line 929, `POST /api/v1/admin/lab-hcorg`)
2. `ingest_lab_results` (~line 963, `POST /api/v1/admin/lab`)

Dependencies: `hmac`, `select`, `AsyncSession`, `Depends`, `Header`, `HTTPException`, `status`, `get_session`, `Batch`, `LabHCorgRequest`, `LabResultsRequest` (from schemas), `_ADMIN_SECRET` (from settings), `recompute_batch_credit` (from credit_engine), `apply_lab_results` (from services.lab)

### `backend/routers/admin.py`
Move (5 routes + `_parse_dt` if not moved in R6):
1. `register_kiln` (~line 2558, `POST /api/v1/admin/kiln`)
2. `register_operator_training` (~line 2570, `POST /api/v1/admin/operator-training`)
3. `register_supervisor_visit` (~line 2580, `POST /api/v1/admin/supervisor-visit`)
4. `register_scale_calibration` (~line 2590, `POST /api/v1/admin/scale-calibration`)
5. `register_annual_verification` (~line 2626, `POST /api/v1/admin/annual-verification`)

Dependencies: `AsyncSession`, `Depends`, `Header`, `status`, `get_session`, all admin request schemas (from schemas), `_require_admin` (from security), `upsert_*` functions (from services.registry)

### `backend/routers/compliance.py`
Move:
1. `batch_compliance` (~line 2728, `GET /api/v1/batches/{batch_uuid}/compliance`)

Dependencies: `uuid`, `select`, `AsyncSession`, `Depends`, `Header`, `HTTPException`, `status`, `get_session`, `Batch`, `_require_admin` (from security), `compliance_view` (from services.compliance)

---

## CRITICAL: Router construction

Each `routers/*.py` file creates an `APIRouter` and decorates its routes on that router (not on `app`):

```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/api/health")
async def health(...):
    ...
```

The routes keep their EXACT same paths (absolute, e.g. `/api/v1/batches`, NOT relative to a prefix).
Do NOT add a `prefix=` to the router — use absolute paths to avoid any behavior change.

---

## STEP 2 — Edit `backend/server.py`

1. **Delete** all middleware functions and route handlers from server.py.
2. **Remove** the `@app.middleware("http")` decorators for `_limit_body_size` and `_rate_limit` from server.py.
3. **Remove** the `observability.install_middleware(app)` call (it moves to R9).
4. **Keep** the `app = FastAPI(...)`, CORS setup, `lifespan`, `UPLOAD_DIR`, and the portal mount — those move in R9.
5. **Add re-export imports** for all moved symbols.
6. **Add router includes** temporarily in server.py (they move to app_factory in R9):
   ```python
   from middleware import _limit_body_size, _rate_limit  # noqa: F401
   # ... all other re-exports ...
   
   # Register middleware in the same order as before
   app.middleware("http")(_limit_body_size)
   app.middleware("http")(_rate_limit)
   observability.install_middleware(app)
   
   # Include all routers
   from routers.health import router as health_router
   from routers.devices import router as devices_router
   from routers.batches import router as batches_router
   from routers.evidence import router as evidence_router
   from routers.media import router as media_router
   from routers.lab import router as lab_router
   from routers.admin import router as admin_router
   from routers.compliance import router as compliance_router
   
   app.include_router(health_router)
   app.include_router(devices_router)
   app.include_router(batches_router)
   app.include_router(evidence_router)
   app.include_router(media_router)
   app.include_router(lab_router)
   app.include_router(admin_router)
   app.include_router(compliance_router)
   ```

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import app, _rl_counters, _RL_MAX_COUNTERS; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
   - This is the highest-risk step — every route moved. If any test fails, it's a missing import or
     re-export. Fix the import, never the test.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R8** — extracted middleware.py + routers/* (21 handlers); server.py ~1180→~250; 416/2 green`
- Commit:
  ```
  refactor(backend): extract middleware.py + routers/* — server.py ~1180→~250 LOC (P4.8/R8)

  Pure relocation, no behavior change. 21 route handlers in domain routers,
  rate-limit infra in middleware.py. Middleware registration order preserved.
  Suite green (416 passed, 2 skipped). Facade re-exports preserve import surface.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
