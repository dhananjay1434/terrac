# dMRV Evolution — Execution Log

Coordinator-maintained. The **M0.1 NOTES** below are pasted into every backend
worker's briefing. Append per-task STATUS lines as the run proceeds.

---

## M0.1 NOTES (read-and-map) — canonical context for all backend tasks

### (a) How tests get a DB session  (`backend/tests/conftest.py`)
- `test_engine` (function-scoped): fresh **SQLite tempfile** via
  `create_async_engine(..., poolclass=NullPool)` + `Base.metadata.create_all`.
  If `DATABASE_URL` starts with `postgresql`, it runs against that server with
  `drop_all/create_all` isolation (dialect-parity lane). **No Alembic in tests**
  — schema is built from `Base.metadata`, so new models MUST be added to
  `models.py` or tests won't see the table.
- `session_factory(test_engine)` → `async_sessionmaker(test_engine, expire_on_commit=False)`.
- `client(session_factory)`: `from server import app, get_session`; overrides
  `app.dependency_overrides[get_session]`; httpx `AsyncClient` over `ASGITransport`.
- **Signed device requests:** `SignedAsyncClient` auto-adds `X-Device-Id` +
  `X-Signature` when absent. Canonical string signed (Ed25519):
  `f"{method}\n{path}\n{op_id}\n{body_hash}\n{device_id}"` where
  `op_id = X-Idempotency-Key header`, `body_hash = sha256(body).hexdigest()`.
  Fixed test identity: `TEST_PUBLIC_KEY_B64` from seed `bytes(range(32))`.
- `registered_device` fixture enrolls via `POST /api/v1/register` with header
  `X-Enrollment-Token` (seed an `EnrollmentToken` row first).
- Telemetry-needing tests insert a real `PyrolysisTelemetry` row with the
  canonical key **`temperature_readings`** (no more global mock).
- Env shims set by conftest: `DATABASE_URL=sqlite+aiosqlite:///:memory:`,
  `DMRV_SKIP_MIGRATIONS=1`, `DMRV_RATELIMIT_ENABLED=0`,
  `DMRV_ALLOW_WEAK_SECRETS=1`, `DMRV_HMAC_SECRET=test-secret`,
  `DMRV_ADMIN_SECRET=test-admin-secret`.
- **Backend test cmd:** `cd backend && python -m pytest tests/<file> -q`.
  Python 3.11.9, SQLAlchemy 2.0.36, deps present.

### (b) Migration pattern  (`backend/alembic/versions/b7c1d2e3f4a5_*.py`)
- Module header vars: `revision`, `down_revision` (linear chain — **coordinator
  serializes all migrations**), `branch_labels=None`, `depends_on=None`.
- `upgrade()` / `downgrade()` use `op.` calls (NOT raw SQL). Column adds/CHECK
  changes wrapped in `with op.batch_alter_table("<table>") as batch_op:`
  (batch mode = SQLite-safe, required for ALTER on SQLite). `import sqlalchemy as sa`.
- Migration self-test: `alembic upgrade head && alembic downgrade -1 && alembic
  upgrade head` on a scratch SQLite file (READ `alembic/env.py`).
- **Tests build schema from `Base.metadata`, not migrations** — so every schema
  task must land BOTH the migration AND the `models.py` mapping.

### (c) Credit-engine telemetry read (M2.5 injection anchor)
- **`backend/credit_engine.py:511-519`** — inside the main compliance function,
  the C10 plausibility call:
  ```python
  c10_reasons.extend(
      derive_plausibility_reasons(
          biomass_input_kg=batch.biomass_input_kg,
          wet_yield_kg=wet_yield,
          min_temp=min_temp,
          temperature_readings=(
              tel_payload.get("temperature_readings") if tel_payload else None
          ),
          moisture_values=_moisture_values,
      )
  )
  ```
  `tel_payload` = parsed `PyrolysisTelemetry.payload_json` (earlier in same fn).
  M2.5 shim adds ONE guarded conditional here: if legacy array missing/empty AND
  `flag_enabled(session,"telemetry_v2",org)` → use
  `telemetry_bridge.temperature_array_for(...)`. Legacy path stays first.

### Signature / auth patterns
- Device-write endpoints: `device_id: str = Depends(verify_signature)` — workers
  must `import` it **exactly as `backend/routers/evidence.py` does** (READ that
  import line; do not guess the module path).
- Portal endpoints: copy the auth `Depends(...)` used in `backend/portal/routes.py`
  (READ it; there's a portal-user dependency).
- Router registration: add new routers in `backend/app_factory.py`
  (coordinator-only file) after the anchor `portal_issuance_router`.

### ⚠️ M0.2 ADAPTATION (the one permitted deviation, per task caveat)
`AppConfig` (`models.py:813-841`) is **single-row** (`config_id` PK default
`"default"`) with a **`flags_json` TEXT** blob — NOT key/value columns. So
`feature_flags.py` reads the `config_id="default"` row, parses `flags_json` as a
dict, and looks up keys `ff.<flag>` / `ff.<flag>.<org_id>` **inside that dict**
(values `"on"/"off"`). All plan semantics preserved: FLAGS tuple unchanged,
org-override-beats-global, default-off (missing row/key → off), never cached
(re-read per call). Documented here per the M0.2 caveat.

---

## Task status log
(appended as tasks complete)
