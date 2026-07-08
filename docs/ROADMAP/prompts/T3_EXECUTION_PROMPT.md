# T3 Execution Prompt — Production Operations

> **Companion to** [`../04_TIER3_PRODUCTION.md`](../04_TIER3_PRODUCTION.md). That file is the *what/why*; this file is the *exact, anchor-verified, do-this-next* script — written the same way as
> [`T1_EXECUTION_PROMPT.md`](T1_EXECUTION_PROMPT.md) / [`T2_EXECUTION_PROMPT.md`](T2_EXECUTION_PROMPT.md).
>
> **Branch:** `remediation/phase-by-phase` · **Base HEAD when written:** `82a6fe0`
> **Discipline (non-negotiable):** one task = one commit = one green gate = one `REMEDIATION_LOG.md` entry. Additive & backward-compatible only. Config read **live from `os.environ`** (survives `importlib.reload`). New deps go into `backend/requirements.txt` in the same commit that imports them.

---

## Anchors verified 2026-07-08 (against current HEAD, NOT the stale line numbers in 04_TIER3)

`server.py` is **2322 lines** now (was 2073 at audit time). Confirmed anchors:

| Symbol | Line | Note |
|---|---|---|
| `db.py` engine (`create_async_engine`) | `db.py:24-28` | `echo=False, future=True` only — no pool args |
| `db.py` `init_db()` + `DMRV_SKIP_MIGRATIONS` gate | `db.py:49-61` | migrations run unless `=="1"` |
| `log = logging.getLogger("dmrv")` / `basicConfig` | `server.py:247-248` | plain text logging today |
| `lifespan` | `server.py:251-255` | |
| CORS middleware | `server.py:268-285` | |
| `_limit_body_size` middleware | `server.py:295-309` | |
| `_rate_limit` middleware (T2.2) | `server.py:366-399` | **outermost-registered → runs first**; new middleware ordering matters |
| `/api/health` (DB probe, T2.6) | `server.py:521-539` | already truthful — compose healthcheck target |
| `verify_signature` (v1+v2) | `server.py:545-611` | |
| `recompute_batch_credit` | `server.py:894-1206` | synchronous, per-evidence — T3.7 target |
| `MediaFile.file_path` write | `server.py:1581-1596` | `UPLOAD_DIR / device / f"{op}.bin"`, local disk |
| `UPLOAD_DIR` | `server.py:401-402` | `Path(__file__).parent / "uploads"` |
| `create_batch` | `server.py:1317` | |
| `upload_media` handler | `server.py:1483-1643` | |
| `_require_admin(x_admin_secret)` | `server.py:1976` | the auth pattern for all read endpoints |
| `batch_compliance` GET | `server.py:2266` | **the ONLY non-health GET today** |
| Alembic head | `f1a2b3c4d5e6` | new migrations set `down_revision` here |
| CI workflow | `.github/workflows/backend-ci.yml` | **tracked** (handoff was stale); single SQLite `tests` job + informational `lint` |

**Route inventory:** every endpoint except `/api/health` and `/api/v1/batches/{uuid}/compliance` is a POST. There is **no list / device / summary read** — T3.4 is a genuine gap, not a duplicate.

**Local tooling available:** Docker **26.1.1** present → T3.2 and the compose gates for T3.3/T3.8 can be *run*, not just written. `.env.example` and `DEPLOYMENT.md` exist. No `backend/scripts/` yet.

**Environment reality:** no git remote yet (T0.1 outstanding), so CI lanes written here **cannot actually execute** until the repo is pushed. Each CI change is gated by "YAML validated + the equivalent commands run locally"; mark the true CI-green as pending-push in the log. Do **not** block T3 on T0 — but call it out.

---

## Baseline gates (must stay green every commit)

- Backend: `cd backend && python -m pytest -q` → **307 passed, 1 skipped, 0 failed** (~90–120s; run in background).
- Flutter: `flutter analyze` → 25 issues / 0 errors (add none); `flutter test` → 153/2/0. *(T3 is backend-only except where noted — Flutter gate only needs re-running if client files change, which T3 does not.)*

---

## Task order (dependency-sorted; each is its own commit)

Recommended execution order differs slightly from numeric order to front-load self-contained, fully-local-testable wins:

1. **T3.1** — engine pool tuning + Postgres CI lane  *(unblocks the "tested on PG" claim; pool tuning is the risky bit)*
2. **T3.4** — read API  *(pure additive value, 100% locally testable, no infra)*
3. **T3.3** — storage abstraction  *(read API's media detail wants the storage key contract)*
4. **T3.5** — observability  *(request-id + JSON logs + /metrics + Sentry)*
5. **T3.2** — Dockerfile + compose + image-boot smoke  *(ties PG + MinIO + health together; locally runnable)*
6. **T3.6** — backup + restore-drill scripts + RPO/RTO docs
7. **T3.8** — load smoke test script + baseline doc
8. **T3.7** — async recompute → **DEFER** (gate says: only after T3.5 metrics prove need). Document as gated, do not implement.
9. **T3.9** — host/TLS/pin-rotation → **DECISION** (needs user to pick platform). Write the decision matrix + document; do not pick unilaterally.

---

## T3.1 — Postgres for real (CI lane + engine pool tuning)

**GOTCHA (the whole risk of this task):** `pool_size` / `max_overflow` are **invalid for SQLite/aiosqlite** engines — SQLAlchemy raises `TypeError: Invalid argument(s) 'pool_size'` because SQLite uses `SingletonThreadPool`/`StaticPool`. The test suite runs on `sqlite+aiosqlite:///:memory:`. So pool args MUST be applied **conditionally on the URL scheme**.

**db.py change (`db.py:24-28`):**
```python
_is_postgres = DATABASE_URL.startswith("postgresql")
_engine_kwargs: dict = {"echo": False, "future": True}
if _is_postgres:
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=int(os.environ.get("DMRV_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("DMRV_POOL_MAX_OVERFLOW", "20")),
    )
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
```
Read pool sizes live is NOT required here (engine built once at import), but keep them env-driven for deploy tuning.

**CI (`.github/workflows/backend-ci.yml`):** add a second job `tests-postgres`:
- `services: postgres:16` (health-checked), `DATABASE_URL=postgresql+asyncpg://dmrv:dmrv@localhost:5432/dmrv`, `DMRV_SKIP_MIGRATIONS=0` (migrations RUN — doubles as migration-integrity gate).
- Steps: install deps → `alembic upgrade head` → **migration round-trip** `alembic downgrade base && alembic upgrade head` → `alembic check` (drift gate; 1.12.1 has it) → `python -m pytest -q`.
- Keep `DMRV_ALLOW_WEAK_SECRETS=1`, `DMRV_HMAC_SECRET`/`DMRV_ADMIN_SECRET` literals matching conftest.

**Local pre-push validation (do this, log it):** spin a throwaway PG via the compose file from T3.2 (or `docker run --rm -e POSTGRES_... -p 5432 postgres:16`), export the asyncpg URL, run the exact round-trip + `alembic check` + pytest locally. `alembic check` may surface **pre-existing** model↔migration drift — if so, do NOT silently rewrite history; log the drift and add a corrective migration (down_revision = `f1a2b3c4d5e6`) or fix the offending column, whichever the drift is.

**Gate:** local PG round-trip + `alembic check` clean + pytest green on PG; SQLite `tests` job unaffected (pool args skipped). CI-green pending-push.

---

## T3.4 — Admin read API (cursor pagination)

**Where:** new endpoints in `server.py` near the other admin GETs (after `batch_compliance`, ~line 2320). All use `_require_admin(x_admin_secret)` (`server.py:1976`). Strict Pydantic response models. **Never expose `file_path`** — return media SHA + counts only.

Endpoints:
| Endpoint | Returns |
|---|---|
| `GET /api/v1/admin/batches?project_id=&device_id=&provisional=&limit=50&cursor=` | rows: `{id, uuid, device_id, project_id, scale_id, status, provisional, reason_count, net_credit, created_at}` + `next_cursor`. **Cursor = last `id`; order by `id` ASC/DESC; NO OFFSET.** `limit` clamped 1..200. |
| `GET /api/v1/admin/batches/{uuid}` | full batch + parsed `lca_audit_json` + evidence counts per table (telemetry/yield/moisture/composite/transport/media). |
| `GET /api/v1/admin/devices` | `{device_id, key_created_at, batch_count, last_activity}`. |
| `GET /api/v1/admin/summary` | `{batches_total, provisional_count, provisional_pct, issued_credit_sum, reason_histogram: {reason: count}}`. |

**Pagination stability rule:** keyset (WHERE id > cursor ORDER BY id LIMIT n), never OFFSET — inserts during pagination must not skip/dupe rows. `test_read_api.py` asserts this by inserting a row mid-pagination.

**Gate:** new `backend/tests/test_read_api.py` — pagination stable under concurrent insert; admin auth enforced (401 without header, `hmac.compare_digest` path); zero `file_path` leakage in any response. Full pytest green.

---

## T3.3 — Object storage for evidence media

**New `backend/storage.py`:** an ABC `EvidenceStorage` with:
- `LocalStorage` — today's behavior (write under `UPLOAD_DIR`), the **default** (`DMRV_STORAGE=local`, unset → local). Preserves current tests unchanged.
- `S3Storage` — `aioboto3` (add to requirements), S3 or MinIO via `DMRV_S3_ENDPOINT`/`DMRV_S3_BUCKET`/`AWS_*`. Selected by `DMRV_STORAGE=s3`.
- Interface: `async put(key: str, data: bytes, *, sha256: str, content_type: str) -> str` (returns stored key), `async get(key) -> bytes`, `async exists(key) -> bool`. Key format: `{device_id}/{operation_id}.bin` (matches today's layout).

**Wire the media handler (`server.py:1581-1596`):** replace the direct `open(...).write()` with `await storage.put(key, content, sha256=..., content_type=...)`; persist the returned key in `MediaFile.file_path` (column is Text — additive semantic change, no migration). Selection read **live from env** at handler call (so tests can flip).

**S3 hardening (document, apply via bucket policy not code):** versioning + object-lock on the evidence bucket; lifecycle rule ONLY for incomplete multipart uploads, never evidence.

**Migration script:** `backend/scripts/migrate_uploads_to_s3.py` (idempotent; skips objects already present with matching SHA).

**Gate:** `test_media_auth.py` still green with LocalStorage (default). New `backend/tests/test_storage.py`: LocalStorage round-trip; S3Storage round-trip against MinIO — **skip-if-no-MinIO** locally (`pytest.mark.skipif` on a `DMRV_S3_ENDPOINT` probe), run for real in the compose CI job. SHA-256 preserved end-to-end.

---

## T3.5 — Observability (JSON logs, request IDs, /metrics, Sentry)

**New deps:** `python-json-logger`, `prometheus-fastapi-instrumentator`, `sentry-sdk[fastapi]` → requirements.txt (same commit).

1. **Request IDs:** new middleware — accept inbound `X-Request-ID` or mint one (UUID4; **but `Math.random`/uuid is fine server-side**), stash on `request.state`, echo in response header. **Middleware ordering:** register it so it wraps the others (request-id must be available to the rate-limit + body-size middlewares' logs). Note the T2.2 rate-limit middleware at `server.py:366`.
2. **Structured JSON logs:** swap `basicConfig` (`server.py:248`) for a `python-json-logger` formatter on the `dmrv` logger. Per-request access log carries `request_id, device_id?, batch_uuid?, operation_id?, method, path, status, latency_ms`. **GPS redaction:** the formatter must drop/round lat/lon — `test_p1_26_log_redaction.py` exists; extend it, don't regress it.
3. **Metrics:** `prometheus-fastapi-instrumentator` → `/metrics`. Add domain gauges/counters: `dmrv_batches_total`, `dmrv_batches_provisional`, `dmrv_reason_total{reason=}`, `dmrv_media_bytes_total`, `dmrv_sync_4xx_total`. **Auth or bind-protect `/metrics`** (admin secret, or document network-level protection). Exclude `/metrics` from the rate limiter (`_rl_bucket`) and from request-id noise.
4. **Sentry:** `sentry_sdk.init(dsn=os.environ.get("DMRV_SENTRY_DSN"), ...)` in lifespan/import — **no-op when DSN unset** (default), `send_default_pii=False`, scrub `buyer_contact`/GPS.
5. **Alert seeds:** document in DEPLOYMENT.md (5xx rate, p95, provisional-ratio spike = methodology-regression detector, health fail).

**Gate:** new `backend/tests/test_observability.py` — response has `X-Request-ID`; a log line is valid JSON with `request_id` and no raw GPS; `/metrics` returns Prometheus text and increments a counter after a request; Sentry init no-ops without DSN. Full pytest green. Redaction test still green.

---

## T3.2 — Dockerfile + compose + image-boot smoke

**`backend/Dockerfile`** (non-root, slim, as in 04_TIER3 §T3.2). Pin `python:3.11-slim`. `HEALTHCHECK` curling `/api/health`.

**`docker-compose.yml`** (repo root): `api` + `postgres:16` + `minio` (for T3.3). Secrets via env (`.env` referenced, `.env.example` documents keys). api depends_on postgres (healthy). api env: real `DATABASE_URL` (asyncpg → postgres service), `DMRV_SKIP_MIGRATIONS=0`, storage=s3 pointing at minio, strong secrets.

**Validate LOCALLY (Docker 26.1.1 is present):** `docker compose build && docker compose up -d && curl -f localhost:8001/api/health` → expect `{"status":"ok"}` after migrations run. Tear down. **This is the "deploys from scratch" proof** — capture the output in the log.

**CI:** add a job that builds the image and boots it against compose PG, curls `/api/health`. Pending-push for true green.

**Gate:** local `docker compose up` → healthy migrated stack; `/api/health` 200. Log the curl output.

---

## T3.6 — Backups with a tested restore

- `backend/scripts/backup.sh` — `pg_dump` (custom format) → object storage (or local dir for dev), timestamped, 30-day retention prune.
- `backend/scripts/restore_drill.sh` — restore latest dump into a **scratch** PG (compose profile or ephemeral container), run `alembic current` + `SELECT count(*) FROM batches`, print result. **A backup never restored is a hope, not a backup.**
- Run the drill once against the compose stack locally; capture output.
- Document **RPO 24h / RTO 2h** in DEPLOYMENT.md.

**Gate:** one successful documented restore drill (local against compose is acceptable evidence; note it's not the prod target yet).

---

## T3.8 — Load smoke test

- `backend/loadtest/locustfile.py` (locust) OR `k6` script: simulate 200 devices × full evidence flow (register → batch → telemetry → yield → moisture ×10 → media 2MB → application), each signing correctly (reuse the crypto path or a pre-registered key set).
- Run against the compose stack; record baseline p50/p95/5xx in `docs/ROADMAP/benchmarks.md`.

**Gate:** zero 5xx at 200 devices; documented p95s. (Local run is a smoke baseline, not the prod SLA.)

---

## T3.7 — Async recompute (DEFER — document only)

Do **not** implement. The tier gate itself says: only after T3.5 observability proves evidence p95 is a problem. Add a short note to the log + a `TODO(T3.7)` near `recompute_batch_credit` (`server.py:894`) describing the debounce-then-queue path, gated on measured latency.

---

## T3.9 — Host / TLS / pin-rotation (DECISION — needs user)

Write a decision matrix (Cloud Run+Cloud SQL+GCS vs Fly.io vs VM+caddy) into DEPLOYMENT.md with the recommendation (Cloud Run least-ops for a pilot fleet), the **cert-pin rotation policy** tradeoff (pin leaf = rotate app config on renewal; pin intermediate/SPKI = survivable renewals — the client pins `DMRV_PINNED_CERT_PEM`), `DMRV_ALLOWED_ORIGIN` + platform secret manager notes. **Do not pick the host unilaterally** — surface the matrix and ask the user to choose before any provisioning.

---

## Exit criteria for T3 (verbatim from 04_TIER3, with local-vs-CI honesty)

- [ ] `docker compose up` from clean checkout → healthy migrated stack (T3.2, **locally proven**).
- [ ] CI runs suite on Postgres with migrations + `alembic check` + image-boot smoke (T3.1/T3.2, **pending push — T0.1**).
- [ ] Evidence media in versioned object storage; host death loses no evidence (T3.3).
- [ ] Ops answers "how many provisional, and why" via read API/metrics without SQL (T3.4/T3.5).
- [ ] One restore drill performed + logged; load baseline recorded (T3.6/T3.8).

**Honesty note for the log:** anything gated only on the absent git remote (CI actually running) is *written and locally-equivalent-verified*, flipped to fully-green when T0.1 lands. Do not claim CI-green while there is no remote.
