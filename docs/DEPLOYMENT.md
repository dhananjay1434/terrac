# dMRV Backend — Deployment Guide

Living deployment reference, built up across Phase P3. Sections land as their
tasks do: media storage (P3.2), Cloud Run runbook (P3.3), observability +
alerting (P3.4).

---

## Media storage (P3.2)

Evidence media (photos, lab certificates) is written behind the `MediaStorage`
abstraction in [`backend/storage.py`](../backend/storage.py). The active backend
is chosen at process start by environment:

| Env | Values | Meaning |
|-----|--------|---------|
| `DMRV_MEDIA_BACKEND` | `local` (default) \| `s3` | Storage implementation. |
| `DMRV_MEDIA_BUCKET` | bucket name | Required when backend is `s3`. |
| `DMRV_S3_ENDPOINT` | URL | S3 endpoint. Set for MinIO / GCS-interop; omit for AWS. |
| `DMRV_S3_ACCESS_KEY` / `DMRV_S3_SECRET_KEY` | creds | Omit to use the platform's ambient credentials (IAM role / workload identity). |
| `DMRV_S3_REGION` | region | Optional. |

**Key model.** `media_files.file_path` stores an *abstract key* for new rows
(e.g. `device-7/op-abc.bin`), never an OS path. Historical rows hold an absolute
filesystem path; `LocalMediaStorage` resolves both, so switching this on is
additive — old rows keep serving from the local disk they were written to.

### Bucket policy (REQUIRED for the `s3` backend)

Evidence is **append-only by policy** — a credit's provenance must never be
silently mutable. Configure the bucket accordingly:

1. **Versioning: ON.** Every overwrite keeps the prior object version. A
   re-submitted lab certificate (same `labcert-<uuid>` key) must not destroy the
   superseded one.
2. **Object Lock / retention: ON where supported** (AWS S3 Object Lock in
   *compliance* mode, or GCS retention policy). Set a retention period at least
   as long as the crediting programme's audit window (Rainbow: keep for the full
   crediting period + audit tail; default 10 years pending methodology sign-off).
3. **Public access: BLOCKED.** All reads go through the authenticated portal
   `/media/{operation_id}` route; the bucket is never world-readable.
4. **Encryption at rest: ON** (SSE-S3/KMS on AWS, Google-managed or CMEK on GCS).
5. **Lifecycle:** do **not** add expiration/deletion rules on the evidence
   prefix — retention governs removal, not lifecycle age-out.

#### AWS S3 (example)

```bash
aws s3api create-bucket --bucket dmrv-evidence-prod --region us-east-1
aws s3api put-bucket-versioning --bucket dmrv-evidence-prod \
  --versioning-configuration Status=Enabled
aws s3api put-object-lock-configuration --bucket dmrv-evidence-prod \
  --object-lock-configuration '{"ObjectLockEnabled":"Enabled","Rule":{"DefaultRetention":{"Mode":"COMPLIANCE","Years":10}}}'
aws s3api put-public-access-block --bucket dmrv-evidence-prod \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

#### GCS (S3-interop; example)

```bash
gcloud storage buckets create gs://dmrv-evidence-prod --location=asia-south1 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://dmrv-evidence-prod --versioning
gcloud storage buckets update gs://dmrv-evidence-prod \
  --retention-period=10y
```

Point the app at GCS via the S3-interop endpoint:
`DMRV_S3_ENDPOINT=https://storage.googleapis.com`, with an HMAC key pair as the
S3 access/secret. (Native GCS credentials work too if you later swap in a GCS
backend; the endpoint-based S3 path avoids a second SDK for now.)

### Local development with MinIO

`docker-compose.yml` ships a `minio` service behind the `storage` profile:

```bash
docker compose --profile storage up -d minio
# create the bucket once (via the console at :9001 or the mc client), then:
DMRV_MEDIA_BACKEND=s3 \
DMRV_MEDIA_BUCKET=evidence \
DMRV_S3_ENDPOINT=http://localhost:9000 \
DMRV_S3_ACCESS_KEY=minioadmin \
DMRV_S3_SECRET_KEY=minioadmin \
  uvicorn server:app --port 8001
```

The `media-s3-smoke` CI job (`.github/workflows/backend-ci.yml`) runs the real
boto3 path against a MinIO service container: write → hash-verify → stream back.

---

## Observability (P3.4)

Wired in [`backend/observability.py`](../backend/observability.py):

- **Structured logs.** Every log line is JSON (`ts/level/logger/msg/request_id`).
  A per-request UUID is minted (or taken from an inbound `X-Request-Id`), bound
  into a contextvar so it appears on every line emitted during the request, and
  echoed back in the `X-Request-Id` response header.
- **Metrics.** `GET /metrics` (Prometheus exposition), **guarded by the
  `X-Metrics-Token` header matching `DMRV_METRICS_TOKEN`** — unset ⇒ endpoint
  closed. Series: `dmrv_requests_total{method,route,status}`,
  `dmrv_request_duration_seconds{route}`, `dmrv_sync_5xx_total{route}`,
  `dmrv_provisional_ratio` (refreshed per scrape), `dmrv_recompute_duration_seconds`.
  Route labels use the **path template** (e.g. `/api/v1/portal/batches/{batch_uuid}`)
  so UUIDs never explode label cardinality.
- **Sentry.** Enabled only when `DMRV_SENTRY_DSN` is set; `traces_sample_rate`
  from `DMRV_SENTRY_TRACES` (default 0.05). `before_send`/`before_breadcrumb`
  scrub `lat`/`lon`/`device_id` (mirrors the client's `beforeBreadcrumb`), and
  `send_default_pii=False`.

### Alerting (configure in your monitoring stack against `/metrics`)

| Alert | Condition | Why |
|-------|-----------|-----|
| **5xx rate** | `rate(dmrv_sync_5xx_total[5m]) > 0` sustained 10 m | Device syncs are failing — data loss risk. |
| **p95 latency** | p95 of `dmrv_request_duration_seconds` > 2 s (JSON routes) for 10 m | Backpressure / DB saturation. |
| **Health-check fail** | `/api/health` non-200, 2 consecutive probes | DB unreachable; container should be recycled. |
| **Provisional-ratio spike** | `dmrv_provisional_ratio` up >20% day-over-day | A capture regression or a systemic corroboration failure in the field. |
| **DB connections** | pool usage > 80% of `DMRV_POOL_SIZE + DMRV_POOL_MAX_OVERFLOW` | Approaching connection exhaustion. |
| **Disk** | evidence volume > 80% (local backend only) | Move to object storage (P3.2) before it fills. |

---

## HMAC key rotation (P3.6)

The server's `lca_signature` (an HMAC over each issued batch's LCA audit) uses
**versioned keys** so the key can be rotated without invalidating any
already-issued signature. Each batch records the key id it was signed under
(`batches.lca_signature_key_id`); verification resolves that id.

- **Legacy (default):** set only `DMRV_HMAC_SECRET`. It is used as key id `k0`;
  rows written before P3.6 (null key id) also resolve to `k0`.
- **Versioned:** set `DMRV_HMAC_KEYS={"k2":"<hex>","k1":"<hex>"}` and
  `DMRV_HMAC_ACTIVE_KEY=k2`. New signatures use the active key; old ones keep
  verifying under their recorded id.

**Rotation procedure (zero downtime, no historical breakage):**

1. Generate a fresh secret, e.g. `k3`.
2. Deploy with `DMRV_HMAC_KEYS` containing **both the new and all still-relevant
   old keys** — e.g. `{"k3":"<new>","k2":"<old>"}` — and
   `DMRV_HMAC_ACTIVE_KEY=k3`. New issuances now sign under `k3`.
3. **Never remove a key id that still has issued signatures you must verify.**
   Dropping a key from `DMRV_HMAC_KEYS` makes those signatures report
   `unverifiable` (by design — no crash), not `invalid`.

Device authentication (Ed25519) is a **separate** mechanism and is unaffected by
this rotation.

---

## Cloud Run deployment (P3.3)

Artifacts: [`deploy/cloudrun.service.yaml`](../deploy/cloudrun.service.yaml)
(service), [`deploy/migrate-job.yaml`](../deploy/migrate-job.yaml) (one-shot
migrations), [`deploy/deploy.sh`](../deploy/deploy.sh) (build → migrate → deploy).

### `[HUMAN]` one-time GCP setup

```bash
export PROJECT_ID=... REGION=asia-south1
gcloud config set project $PROJECT_ID

# Artifact Registry (container images)
gcloud artifacts repositories create dmrv --repository-format=docker --location=$REGION

# Cloud SQL Postgres (private IP recommended)
gcloud sql instances create dmrv-pg --database-version=POSTGRES_16 \
  --tier=db-custom-1-3840 --region=$REGION --storage-auto-increase
gcloud sql databases create dmrv --instance=dmrv-pg
gcloud sql users create dmrv --instance=dmrv-pg --password='<strong>'
# Connection name -> deploy/*.yaml CLOUDSQL_CONNECTION (project:region:dmrv-pg)

# GCS evidence bucket (see "Media storage" above for versioning/retention)
gcloud storage buckets create gs://dmrv-evidence-prod --location=$REGION \
  --uniform-bucket-level-access
gcloud storage buckets update gs://dmrv-evidence-prod --versioning --retention-period=10y
# GCS S3-interop HMAC key for DMRV_S3_ACCESS_KEY/SECRET
gcloud storage hmac create <service-account>@$PROJECT_ID.iam.gserviceaccount.com

# Secrets (Secret Manager — never env-in-yaml). Generate fresh 32-byte values.
printf '%s' 'postgresql+asyncpg://dmrv:<pw>@/dmrv?host=/cloudsql/<CONN>' \
  | gcloud secrets create dmrv-database-url --data-file=-
printf '%s' '{"k1":"<hex>"}'    | gcloud secrets create dmrv-hmac-keys      --data-file=-
printf '%s' '<admin-secret>'    | gcloud secrets create dmrv-admin-secret   --data-file=-
printf '%s' '<metrics-token>'   | gcloud secrets create dmrv-metrics-token  --data-file=-
printf '%s' '<sentry-dsn>'      | gcloud secrets create dmrv-sentry-dsn     --data-file=-
printf '%s' '<gcs-access>'      | gcloud secrets create dmrv-gcs-hmac-access --data-file=-
printf '%s' '<gcs-secret>'      | gcloud secrets create dmrv-gcs-hmac-secret --data-file=-
# Grant the Cloud Run service account secretmanager.secretAccessor + cloudsql.client.
```

### Deploy (repeatable)

```bash
PROJECT_ID=$PROJECT_ID REGION=$REGION ./deploy/deploy.sh
```

`deploy.sh` builds the `backend/` image, applies + **executes the migration Job
first** (so instances never race Alembic), then replaces the service revision
and prints the URL.

### Key decisions

- **min-instances 1**: cold starts + first-request latency hurt device sync.
- **max-instances 1**: the rate limiter (`_rl_counters`) and the recompute
  coalescing lock are per-process/in-memory. Raising max-instances gives
  per-instance limits (a flooder gets `N×` the cap) and un-coalesced recomputes.
  Keep max 1 for the pilot; lift only after moving both to a shared store (Redis).
- **Migrations off the service** (`DMRV_SKIP_MIGRATIONS=1`) + a Cloud Run Job.
- **TLS / pinning**: Cloud Run terminates TLS with Google-rotated leaf certs, so
  SPKI/leaf pinning on the client would break on every rotation. **Default:
  system trust on Cloud Run** — build the app with `--dart-define DMRV_TLS_TRUST=system`
  (see `RELEASE_CHECKLIST.md`). The pinning path is retained for self-hosted
  deployments with a stable cert (`DMRV_TLS_TRUST=pinned` + `DMRV_PINNED_CERT_PEM`).

### Exit criterion `[HUMAN]`

A real phone (release build, `DMRV_TLS_TRUST=system`, `DMRV_API_BASE_URL` = the
Cloud Run URL) enrolls and syncs one batch over TLS; the portal is served from
the same origin.
