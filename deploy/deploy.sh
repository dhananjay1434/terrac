#!/usr/bin/env bash
# P3.3 — build, push, migrate, deploy the dMRV API to Cloud Run.
# Idempotent. Assumes the [HUMAN] one-time setup below is done and gcloud is
# authenticated against the target project.
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID}"
: "${REGION:?set REGION e.g. asia-south1}"
: "${REPO:=dmrv}"                 # Artifact Registry repo
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/dmrv-api:$(git rev-parse --short HEAD)"

echo "==> Build + push $IMAGE (context = backend/)"
gcloud builds submit backend --tag "$IMAGE" --project "$PROJECT_ID"

echo "==> Render manifests with this image"
tmp="$(mktemp -d)"
sed "s#IMAGE#${IMAGE}#g" deploy/migrate-job.yaml > "$tmp/migrate-job.yaml"
sed -e "s#IMAGE#${IMAGE}#g" -e "s#REGION#${REGION}#g" \
    deploy/cloudrun.service.yaml > "$tmp/cloudrun.service.yaml"

echo "==> Apply + run the migration Job (owns Alembic; service skips it)"
gcloud run jobs replace "$tmp/migrate-job.yaml" --region "$REGION" --project "$PROJECT_ID"
gcloud run jobs execute dmrv-migrate --region "$REGION" --project "$PROJECT_ID" --wait

echo "==> Deploy the service revision"
gcloud run services replace "$tmp/cloudrun.service.yaml" --region "$REGION" --project "$PROJECT_ID"

echo "==> URL:"
gcloud run services describe dmrv-api --region "$REGION" --project "$PROJECT_ID" \
  --format 'value(status.url)'

rm -rf "$tmp"
