import argparse
import asyncio
import json
import logging

from sqlalchemy import select

from db import SessionLocal
from models import (
    MediaFile,
    PyrolysisTelemetry,
    Batch,
    EndUseApplication,
    MoistureReading,
    CompositePileSample,
)

log = logging.getLogger("dmrv.backfill")
logging.basicConfig(level=logging.INFO)


def _index_media(all_media):
    """Index media by (batch_uuid, sha256_hash) -> [MediaFile].

    The per-rule sha-match lookups below all key on this pair, so building it
    once turns each rule from an N+1 stream of round-trips into in-memory dict
    hits. Keys are stable across the rules' mutations (they only touch
    capture_type / capture_type_verified, never batch_uuid / sha256_hash)."""
    idx: dict = {}
    for m in all_media:
        idx.setdefault((m.batch_uuid, m.sha256_hash), []).append(m)
    return idx


def _label_from_evidence_table(rows, capture_type, media_by_key, batch_hashes, counts_key, counts) -> None:
    """Classify photos whose sha256 matches an evidence-table row's own
    submitted record (moisture_readings / composite_pile_samples). Same
    payload-parse + sha-match, source-HINT pattern as the end_use rule (2b):
    matched against the operator's own record, so capture_type_verified stays
    False — NOT corroborated against independent signed telemetry.

    Never overrides the batch-anchor image: if a reading reused the batch's
    anchor photo (same sha == batches.sha256_hash), that photo is left for the
    trust-root batch_photo rule, which labels it verified=True.

    In-memory equivalent of the original per-row `SELECT media WHERE batch_uuid
    AND sha256_hash AND capture_type IS NULL` — same filter (capture_type is
    None), same skip-anchor guard, driven off the prebuilt index."""
    for r in rows:
        try:
            sha = json.loads(r.payload_json).get("sha256_hash")
        except Exception:
            continue
        if not sha:
            continue
        sha = str(sha).lower()
        if batch_hashes.get(r.batch_uuid) == sha:
            continue  # this is the batch anchor — batch_photo rule owns it
        for m in media_by_key.get((r.batch_uuid, sha), []):
            if m.capture_type is None:
                m.capture_type = capture_type
                counts[counts_key] += 1


async def backfill(session, apply: bool = False) -> dict:
    """Classify media_files.capture_type by rule, in a single transaction.

    Behaviour is identical to the original per-rule implementation (asserted by
    tests/test_backfill_media_capture_types.py); the only change is data access:
    every row is bulk-loaded ONCE up front and all sha-matching happens in
    memory, so this survives a high-latency remote connection (the original
    N+1 stream of ~hundreds of sequential round-trips got the socket dropped
    against Render's free-tier Postgres). Rule ORDER is preserved because each
    rule's filter (capture_type IS NULL / capture_type_verified == False) reads
    the mutations the earlier rules made to the same ORM objects."""
    counts = {
        "telemetry": 0,
        "lab_certificate": 0,
        "batch_photo": 0,
        "end_use": 0,
        "moisture": 0,
        "composite_sample": 0,
        "unchanged": 0,
    }

    # --- Bulk load everything once (6 queries total) ---
    all_media = (await session.execute(select(MediaFile))).scalars().all()
    tels = (await session.execute(select(PyrolysisTelemetry))).scalars().all()
    applications = (await session.execute(select(EndUseApplication))).scalars().all()
    moistures = (await session.execute(select(MoistureReading))).scalars().all()
    composites = (await session.execute(select(CompositePileSample))).scalars().all()
    batches = (await session.execute(select(Batch.batch_uuid, Batch.sha256_hash))).all()
    batch_hashes = {b.batch_uuid: b.sha256_hash for b in batches}

    media_by_key = _index_media(all_media)

    # 1. Telemetry rule — inlined from services.evidence.label_media_from_telemetry
    # (same semantics: match batch_uuid + sha256, stamp stage on any not-yet-
    # verified photo; the signed telemetry is the trust root so verified=True).
    # Inlined rather than called per-row to keep it off the N+1 path.
    for t in tels:
        try:
            payload = json.loads(t.payload_json)
        except Exception:
            payload = {}
        for e in payload.get("smoke_evidence", []) or []:
            if not isinstance(e, dict):
                continue
            stage, sha = e.get("stage"), e.get("sha256")
            if not stage or not sha:
                continue
            for m in media_by_key.get((t.batch_uuid, str(sha).lower()), []):
                if not m.capture_type_verified:
                    m.capture_type = str(stage)[:64]
                    m.capture_type_verified = True
                    counts["telemetry"] += 1

    # 2. Lab certificates: operation_id starts with labcert- -> lab_certificate, verified True
    for m in all_media:
        if m.operation_id and m.operation_id.startswith("labcert-") and not m.capture_type_verified:
            m.capture_type = "lab_certificate"
            m.capture_type_verified = True
            counts["lab_certificate"] += 1

    # 2b. Farmer end-use photo (legacy rows predating the app-side fix that
    # stamps capture_type=end_use at capture time). Payload parse + sha256 match;
    # source HINT (matched to the farmer's own record), so verified stays False.
    for app in applications:
        try:
            payload = json.loads(app.payload_json)
        except Exception:
            continue
        sha = payload.get("farmer_photo_sha256")
        if not sha:
            continue
        for m in media_by_key.get((app.batch_uuid, str(sha).lower()), []):
            if not m.capture_type_verified:
                m.capture_type = "end_use"
                counts["end_use"] += 1

    # 2c. Moisture (C2) + composite-pile (C4) photos — the previously-NULL
    # evidence that landed under "Other / Uncategorized". Runs BEFORE the
    # batch-anchor rule and skips any reading that reused the anchor image, so
    # the trust-root batch_photo classification still wins for that shot.
    _label_from_evidence_table(moistures, "moisture", media_by_key, batch_hashes, "moisture", counts)
    _label_from_evidence_table(
        composites, "composite_sample", media_by_key, batch_hashes, "composite_sample", counts
    )

    # 3. Batch anchor photo: sha256_hash == its batch's batches.sha256_hash ->
    # batch_photo, verified True. Only rows still unclassified (capture_type IS
    # None AND not verified) — the same "already classified" test as before, so
    # 2b/2c's just-labeled (verified=False) rows are excluded via capture_type.
    for m in all_media:
        if m.capture_type is None and not m.capture_type_verified:
            if m.batch_uuid in batch_hashes and m.sha256_hash == batch_hashes[m.batch_uuid] and m.sha256_hash is not None:
                m.capture_type = "batch_photo"
                m.capture_type_verified = True
                counts["batch_photo"] += 1
            else:
                counts["unchanged"] += 1

    if apply:
        await session.commit()
    else:
        await session.rollback()

    return counts


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually commit changes to the DB")
    args = parser.parse_args()

    async with SessionLocal() as session:
        counts = await backfill(session, apply=args.apply)
        log.info(f"Backfill counts (apply={args.apply}): {counts}")

if __name__ == "__main__":
    asyncio.run(main())
