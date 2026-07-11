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
