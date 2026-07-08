# Tier 3 — Production Operations: "Deployable, Observable, Recoverable"

> **Benchmark when this tier is green:** one command deploys the backend against Postgres + object storage; an operator can see traffic, errors, and batch state without SSH or DB access; the database survives a host loss with a **tested** restore; and the API supports the reads a dashboard/verifier portal needs. **This is the bar for real buyers and unsupervised fleets.**
>
> **Total effort: ~2 weeks.**

---

## T3.1 — Postgres for real (CI lane + staging)

- **Where:** `db.py:24-28` (engine, default pool), `.github/workflows/backend-ci.yml`, `backend/alembic/`.
- **Why:** the suite runs on in-memory SQLite; production is declared Postgres (`backend/.env.example`). Divergences (JSON handling, timezone semantics, CheckConstraint behavior, `PG_UUID`) are untested.
- **What:**
  1. CI: add a second job `tests-postgres` with a `postgres:16` service container, `DATABASE_URL=postgresql+asyncpg://…`, `DMRV_SKIP_MIGRATIONS=0` so **migrations actually run** — this doubles as the migration-integrity gate the repo lacks.
  2. Add a migration round-trip step: `alembic upgrade head && alembic downgrade base && alembic upgrade head`.
  3. Engine options for prod: `create_async_engine(url, pool_pre_ping=True, pool_size=int(env("DMRV_POOL_SIZE","10")), max_overflow=20)`.
  4. Add a models↔migrations drift check: `alembic check` (Alembic ≥1.9 — the pinned 1.12.1 has it) as a CI step.
- **Gate:** both CI lanes green; `alembic check` clean.
- **Effort:** M/L.

## T3.2 — Containerize: real Dockerfile + compose (DEPLOYMENT.md currently describes files that don't exist)

- **Where:** new `backend/Dockerfile`, `docker-compose.yml` at root; rewrite `DEPLOYMENT.md` (see T4.10).
- **What:**
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY backend/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY backend/ .
  RUN useradd -r dmrv && chown -R dmrv /app
  USER dmrv
  EXPOSE 8001
  CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
  ```
  Compose: `api` + `postgres:16` (+ `minio` after T3.3), secrets via env, healthcheck hitting `/api/health` (truthful after T2.6). Add a CI job that builds the image and boots it against the compose Postgres, curling `/api/health` — the "deploys from scratch" proof.
- **Gate:** `docker compose up` → healthy stack on a clean machine.
- **Effort:** M.

## T3.3 — Object storage for evidence media

- **Where:** `UPLOAD_DIR = Path(__file__).parent / "uploads"` (server.py:265-266); write path in the media handler (server.py:1355-1356); `MediaFile.file_path` column.
- **Why:** local disk = no durability, no horizontal scale, evidence loss on host death — evidence *is* the product.
- **What:**
  1. New `backend/storage.py` with a two-implementation interface: `LocalStorage` (today's behavior, default for dev) and `S3Storage` (`boto3`/`aioboto3`, S3 or MinIO), selected by `DMRV_STORAGE=local|s3` + bucket/creds env.
  2. Media handler streams to storage backend; persist the storage key (e.g. `s3://bucket/device_id/operation_id.jpg`) in `MediaFile.file_path` — additive semantic change, column already Text.
  3. Enable bucket versioning + object lock (evidence immutability is a verifier selling point); lifecycle rule only for incomplete multipart uploads, never for evidence.
  4. Migration script for existing pilot uploads (`backend/scripts/migrate_uploads_to_s3.py`).
- **Gate:** `test_media_auth.py` suite passes against both backends (parametrize with MinIO in the compose CI job); upload → object exists with correct SHA-256 metadata.
- **Effort:** L.

## T3.4 — Read API with pagination (the missing half of the API)

- **Where:** new endpoints in `server.py` (or `api_read.py` after T4.1 splits modules). Today the ONLY read is single-batch admin compliance (server.py:2033-2073) — no list, no device view, no dashboard possible without SQL.
- **What (all admin-authenticated with the existing `X-Admin-Secret` pattern; device-scoped reads can come later):**
  | Endpoint | Returns |
  |---|---|
  | `GET /api/v1/admin/batches?project_id=&device_id=&provisional=&limit=50&cursor=` | id, uuid, device, project, status, provisional, reasons count, net_credit, created — cursor-paginated (order by `id`, cursor = last id; no OFFSET) |
  | `GET /api/v1/admin/batches/{uuid}` | full batch + parsed `lca_audit_json` + evidence counts (telemetry/yield/moisture/composite/transport/media rows) |
  | `GET /api/v1/admin/devices` | device_id, key created_at, batch count, last activity |
  | `GET /api/v1/admin/summary` | totals: batches, provisional %, issued credit sum, per-reason histogram (drives any ops dashboard) |
  Response models strict Pydantic; never expose `file_path` internals (return media SHA + a presigned-URL endpoint instead, per T3.3).
- **Gate:** new `test_read_api.py`: pagination stable under inserts; admin auth enforced; no path leakage.
- **Effort:** L.

## T3.5 — Observability: structured logs, metrics, correlation

- **Where:** logging setup (server.py:200); middleware stack (server.py:220+).
- **What:**
  1. **Structured JSON logs:** `python-json-logger`; every request log carries `request_id`, `device_id` (when authenticated), `batch_uuid`, `operation_id`, latency, status. Redact GPS coordinates at the formatter (`test_p1_26_log_redaction.py` already exists — extend it).
  2. **Request IDs:** middleware generating `X-Request-ID` (accept inbound), echoed in responses and logs.
  3. **Metrics:** `prometheus-fastapi-instrumentator` → `/metrics` (bind-protect it or auth it): request histograms + domain gauges — `dmrv_batches_total`, `dmrv_batches_provisional`, `dmrv_reason_total{reason=…}`, `dmrv_media_bytes_total`, `dmrv_sync_4xx_total`.
  4. **Sentry (server-side):** `sentry-sdk[fastapi]`, DSN via env, PII scrubbing on.
  5. **Alert seeds** (wherever you host): 5xx rate, p95 latency, provisional-ratio spike (methodology regression detector!), health-check fail.
- **Gate:** logs are one-JSON-per-line with request_id; `/metrics` scrapes; forced error appears in Sentry.
- **Effort:** L.

## T3.6 — Backups with a tested restore

- **What:** nightly `pg_dump` (or provider snapshots) to object storage, 30-day retention; media bucket already versioned (T3.3). **A backup that has never been restored is a hope, not a backup:** add a monthly (or CI-cron) restore drill — restore latest dump into a scratch Postgres, run `alembic current` + `SELECT count(*) FROM batches`, post result. Document RPO (24h) / RTO (2h) in DEPLOYMENT.md.
- **Gate:** one successful documented restore drill.
- **Effort:** M.

## T3.7 — Async recompute (only when scale demands)

- **Where:** `recompute_batch_credit` (server.py:718-973) runs synchronously inside every evidence request — 7+ queries per call; concurrent evidence for one batch recomputes redundantly (safe, but wasteful and latency-y on mobile networks).
- **What (defer until p95 latency or DB load says so):** move recompute to a background task — smallest viable step is FastAPI `BackgroundTasks` with a per-batch debounce (skip if a recompute for this batch ran <2s ago); full step is a queue (arq/Redis). Evidence endpoints then return after persisting the row (contract unchanged — they already don't return the credit).
- **Gate:** load test (T3.8) shows evidence p95 < 300ms server-side; recompute correctness suite unchanged.
- **Effort:** L. **Do not do this before observability (T3.5) exists to prove it's needed.**

## T3.8 — Load smoke test

- **What:** a `locust`/`k6` script simulating 200 devices × full evidence flow (batch → telemetry → yield → moisture ×10 → media 2MB → application). Run against the compose stack in CI-nightly or manually pre-release. Record baseline numbers in `docs/ROADMAP/benchmarks.md`.
- **Gate:** zero 5xx at 200 devices; documented p95s.
- **Effort:** M.

## T3.9 — Deployment target decision + TLS

- **What:** pick the actual host (Cloud Run / Fly.io / a VM+caddy — for a pilot fleet, Cloud Run + Cloud SQL + GCS is the least ops). Whatever the choice: TLS terminated with a real cert (the client **pins** it — coordinate `DMRV_PINNED_CERT_PEM` rotation policy: pin the leaf = rotate app config on renewal; pin an intermediate/SPKI = survivable renewals — **decide and document**, this trips real fleets), `DMRV_ALLOWED_ORIGIN` set explicitly, secrets in the platform secret manager.
- **Gate:** staging URL live; a real device build syncs against it end-to-end.
- **Effort:** M–L depending on platform.

---

## ✅ Tier 3 exit criteria (the benchmark, verbatim)

- [ ] `docker compose up` (or platform deploy) from a clean checkout → healthy, migrated, TLS'd stack.
- [ ] CI runs the suite on Postgres **with migrations**, plus `alembic check`, plus an image-boot smoke test.
- [ ] Evidence media lives in versioned object storage; a host can die without losing a byte of evidence.
- [ ] Ops can answer "how many provisional batches, and why" from the read API/metrics without SQL.
- [ ] One restore drill performed and logged. Load baseline recorded.

**The system is now a service, not a script: it can take real traffic from real devices for a real customer and survive the boring disasters.**
