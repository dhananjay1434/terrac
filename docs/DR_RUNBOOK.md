# dMRV Disaster-Recovery Runbook (P3.5)

Backup strategy and the step-by-step restore for the dMRV backend
(Cloud SQL Postgres + GCS evidence media).

- **RPO (max data loss): 24 h** — nightly automated backups, tightened to
  minutes wherever PITR (point-in-time recovery) is enabled.
- **RTO (max downtime): 2 h** — restore a backup to a new instance, run the
  verifier, repoint the service.

> Status: `[ ] drill NOT yet performed`. A human must run one restore on staging
> and initial + date this line (see "Drill log" at the bottom).

---

## What is backed up

| Asset | Mechanism | Retention |
|-------|-----------|-----------|
| Postgres (all batch/evidence/audit rows) | Cloud SQL **automated backups + PITR** | 7 daily backups; PITR window (WAL) 7 days |
| Evidence media (photos, lab certs) | **GCS object versioning** (P3.2) | versioning ON + object retention (10y); no lifecycle expiry on the evidence prefix |
| App config / secrets | Secret Manager (versioned) | all versions retained |
| Schema | Alembic migrations in git | git history |

### Enable (one-time, `[HUMAN]`)

```bash
# Cloud SQL: 7 daily automated backups + PITR
gcloud sql instances patch dmrv-pg \
  --backup-start-time=18:30 \
  --retained-backups-count=7 \
  --enable-point-in-time-recovery \
  --retained-transaction-log-days=7

# GCS media backup = versioning (already set in P3.2 bucket policy)
gcloud storage buckets update gs://dmrv-evidence-prod --versioning
```

---

## Restore procedure

### 1. Pick a recovery point

```bash
gcloud sql backups list --instance=dmrv-pg
# For PITR, choose a timestamp inside the WAL window instead of a backup id.
```

### 2. Restore Postgres to a NEW instance

Never restore in place — restore to a fresh instance so the current (possibly
corrupt) one stays available for comparison.

```bash
# From a backup:
gcloud sql instances clone dmrv-pg dmrv-pg-restored --backup-id=BACKUP_ID
# Or point-in-time:
gcloud sql instances clone dmrv-pg dmrv-pg-restored \
  --point-in-time='2026-07-11T09:00:00Z'
```

### 3. Media

GCS media is versioned and was never deleted, so the live bucket is the media of
record. If a bad delete/overwrite is the incident, restore affected objects to
their prior version:

```bash
# List versions of one object
gcloud storage ls -a gs://dmrv-evidence-prod/<device>/<op>.bin
# Restore a specific generation
gcloud storage cp gs://dmrv-evidence-prod/<obj>#<generation> gs://dmrv-evidence-prod/<obj>
```

### 4. Verify BEFORE cutting traffic

Run the verifier against the restored DB + the media store. It counts rows and
spot-checks media object hashes against `media_files.sha256_hash`:

```bash
DMRV_MEDIA_BACKEND=s3 DMRV_MEDIA_BUCKET=dmrv-evidence-prod \
DMRV_S3_ENDPOINT=https://storage.googleapis.com \
DMRV_S3_ACCESS_KEY=... DMRV_S3_SECRET_KEY=... \
  python backend/scripts/verify_restore.py \
    --database-url 'postgresql+asyncpg://dmrv:<pw>@<restored-host>:5432/dmrv' \
    --media-sample 50
```

`RESTORE OK` (exit 0) ⇒ row counts are plausible and every sampled media object
re-hashes to its recorded digest. Any `MISMATCH`/`MISSING` (exit 1) ⇒ the DB and
object store are from inconsistent points — do NOT cut over; pick another point.

### 5. Repoint the service

Update the `dmrv-database-url` secret to the restored instance and redeploy
(`deploy/deploy.sh`), or update the Cloud SQL connection annotation and
`gcloud run services replace`. Confirm `/api/health` returns `db: ok`, then
restore traffic.

### 6. Post-incident

- Keep the failed instance until root cause is understood.
- Note the actual RPO/RTO achieved in the drill log below.

---

## Drill log

| Date | Operator | RPO achieved | RTO achieved | Notes |
|------|----------|--------------|--------------|-------|
| _pending_ | | | | first staging drill not yet run |
