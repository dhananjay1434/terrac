# 03 — Backend Architecture & API (FastAPI + SQLAlchemy + Postgres)

`backend/` is ~1.1k LOC of application code (`server.py`, `models.py`, `db.py`,
`lca_engine.py`) plus Alembic and a sizable test suite. The bones are
reasonable (async SQLAlchemy 2.0, Pydantic v2, Alembic, idempotency intent), but
the implementation is half-finished and inconsistent.

---

## API design

### 🔴 Half the API is stubs (see `02_CRITICAL_BUGS.md` BUG-2)
`/telemetry`, `/yield`, `/metadata`, `/application` take untyped `dict`, validate
one field, persist nothing. A real API surface for the four follow-on data
domains must exist before any feature work depends on them.

### 🟠 No read API exists
There are no `GET` endpoints for batches/media/credits. The dashboard
(`dashboard_screen.dart`) is therefore driven purely from the local Drift DB
(`dashboard_stats_v` view, `app_database.dart:58-63`). That's fine for an
offline app, but it means **the server is write-only and cannot be a source of
truth, audit, or reconciliation** — a strange property for a registry backend.
There is no way to detect that the client and server have diverged.

### 🟠 Inconsistent idempotency contract
- Batches/media use `X-Idempotency-Key`; media derives its key as
  `${operationId}_media` on the client (`sync_queue_manager.dart:368`).
- The stub endpoints ignore idempotency entirely.
- `BatchResponse.duplicate` semantics differ between the duplicate path (200 +
  `duplicate=True`) and race path. There is no single documented contract.

### 🟡 `extra="forbid"` + a literal field named `extra_field`
`server.py:118-119` declares `extra_field: Optional[str]` *and* `extra="forbid"`.
So a field literally called `extra_field` is allowed but any other extra is
rejected. This looks like a leftover from a test and is a code smell that
directly contributes to BUG-1's confusion.

---

## Data model (`models.py`)

### 🟠 `PyrolysisTelemetry` / `YieldMetrics` / `EndUseApplication` have no write path
The tables exist and are in the baseline migration, but nothing inserts into
them (the endpoints are stubs). Dead schema.

### 🟠 Anchoring via non-unique `sha256_hash`
`Batch.sha256_hash` and `MediaFile.sha256_hash` are `String(64)` **without a
unique constraint**, yet code does `scalar_one_or_none()` on them (BUG-7). The
FK from `media_files.batch_uuid → batches.batch_uuid` is correct, but anchoring
should drive off that FK, supplied explicitly, not off content-hash lookups.

### 🟡 Mixed UUID typing
`Batch.batch_uuid` is `PG_UUID(as_uuid=True)` (Postgres-specific), while
`PyrolysisTelemetry.telemetry_uuid` etc. are `String(36)`. The Postgres-only UUID
type also means the `sqlite+aiosqlite` dev/test path behaves differently from
prod — schema/behavior drift between environments.

### 🟡 `received_at` defaults are Python-side `lambda`, not DB-side
Acceptable, but combined with `expire_on_commit=False` and manual `refresh`
calls it's easy to read stale values. Prefer `server_default=func.now()` for
audit-grade timestamps.

---

## Persistence & migrations (`db.py`, `alembic/`)

### 🟠 `init_db()` runs Alembic `upgrade head` on every startup, in a thread
**`db.py:48-55`** — Running migrations automatically at boot is risky for a
real registry (no review gate, races across replicas, partial upgrades). It also
does `DATABASE_URL.replace("+asyncpg","")` to get a sync URL — brittle string
surgery that silently does the wrong thing for non-asyncpg URLs (e.g.
`sqlite+aiosqlite` stays async and Alembic's sync engine then mismatches).

### 🟠 Prod/dev DB engines diverge
`.env` → Postgres; `.env.example` → `sqlite+aiosqlite:///./dmrv.db`; a committed
`backend/dmrv.db` exists. Tests likely run on SQLite while prod is Postgres. The
`PG_UUID` columns and any Postgres-specific behavior won't be exercised by the
SQLite tests → false confidence.

### 🟡 `DMRV_SKIP_MIGRATIONS` escape hatch
`db.py:50` lets startup skip migrations via env — handy for tests, dangerous if
ever set in prod (server starts against an un-migrated DB and fails at first
write).

---

## Robustness / correctness

| # | Issue | Location |
|---|-------|----------|
| 🟠 | Race-recovery `scalar_one()` can raise on `operation_id` collisions | `server.py:293-305` (BUG-8) |
| 🟠 | Whole upload buffered in memory **twice** (`bytearray` + `bytes(buf)`) up to 10 MB/request → memory pressure under load | `server.py:398-409` |
| 🟡 | `import re` inside the request handler (`server.py:361`) | minor |
| 🟡 | No rate limiting / request size limit beyond the manual 10 MB media cap; `register` is unauthenticated *and* unthrottled | `server.py:196` |
| 🟡 | `logging.basicConfig(level=INFO)` at import; no structured logging, no request id | `server.py:37` |
| 🟡 | Health check doesn't check DB connectivity | `server.py:146-152` |

---

## What's actually good here
- Pydantic v2 validation on `BatchPayload` (ranges, hex check, model validator).
- Idempotency + race-handling *intent* on `batches`/`media` (just incomplete).
- Path-traversal guard on uploads (`server.py:419-438`) is correct and
  defense-in-depth (regex + `is_relative_to`).
- A real, focused test suite (`backend/tests/*` — 16 files incl. P0/P1 cases).
  The problem is the tests validate the current (broken/stub) behavior; they
  need contract tests that exercise the *real client payloads* and assert
  persistence, not just status codes.
