import argparse
import asyncio
import json
import logging

from sqlalchemy import select

from db import async_sessionmaker
from models import MediaFile, PyrolysisTelemetry, Batch, EndUseApplication
from services.evidence import label_media_from_telemetry

log = logging.getLogger("dmrv.backfill")
logging.basicConfig(level=logging.INFO)

async def backfill(session, apply: bool = False) -> dict:
    counts = {
        "telemetry": 0,
        "lab_certificate": 0,
        "batch_photo": 0,
        "end_use": 0,
        "unchanged": 0,
    }

    # 1. Telemetry rule
    # Iterate all telemetry and call label_media_from_telemetry
    tels = (await session.execute(select(PyrolysisTelemetry))).scalars().all()
    for t in tels:
        try:
            payload = json.loads(t.payload_json)
        except Exception:
            payload = {}
        c = await label_media_from_telemetry(session, t.batch_uuid, payload.get("smoke_evidence", []))
        counts["telemetry"] += c

    # 2. Lab certificates
    # rows whose operation_id starts with labcert- -> capture_type="lab_certificate", verified True
    labcert_medias = (await session.execute(
        select(MediaFile)
        .where(MediaFile.operation_id.startswith("labcert-"))
        .where(MediaFile.capture_type_verified == False)
    )).scalars().all()

    for m in labcert_medias:
        m.capture_type = "lab_certificate"
        m.capture_type_verified = True
        session.add(m)
        counts["lab_certificate"] += 1

    # 2b. Farmer end-use photo (legacy rows predating the app-side fix that
    # stamps capture_type=end_use at capture time). The end-use record stores
    # its fields as JSON, not columns, so this is a payload parse + sha256
    # match rather than a column join — mirrors label_media_from_telemetry's
    # pattern. Marked capture_type_verified=False: this is a source HINT
    # (matched by hash to the farmer's own submitted record), not corroborated
    # against independent signed telemetry the way burn-stage photos are.
    applications = (await session.execute(select(EndUseApplication))).scalars().all()
    for app in applications:
        try:
            payload = json.loads(app.payload_json)
        except Exception:
            continue
        sha = payload.get("farmer_photo_sha256")
        if not sha:
            continue
        rows = (
            await session.execute(
                select(MediaFile)
                .where(MediaFile.batch_uuid == app.batch_uuid)
                .where(MediaFile.sha256_hash == str(sha).lower())
                .where(MediaFile.capture_type_verified == False)
            )
        ).scalars().all()
        for m in rows:
            m.capture_type = "end_use"
            session.add(m)
            counts["end_use"] += 1

    # 3. Batch anchor photo
    # rows whose sha256_hash equals their batch's batches.sha256_hash -> capture_type="batch_photo", verified True
    # Excludes rows the end_use rule (2b) just labeled this run — capture_type
    # IS NOT NULL is the "already classified" test, since 2b intentionally
    # leaves capture_type_verified False (source hint, not telemetry-verified).
    all_medias = (await session.execute(
        select(MediaFile)
        .where(MediaFile.capture_type_verified == False)
        .where(MediaFile.capture_type.is_(None))
    )).scalars().all()

    # Pre-fetch batches for quick lookup (if many, might need join, but small dataset is fine)
    batches = (await session.execute(select(Batch.batch_uuid, Batch.sha256_hash))).all()
    batch_hashes = {b.batch_uuid: b.sha256_hash for b in batches}

    for m in all_medias:
        if m.batch_uuid in batch_hashes and m.sha256_hash == batch_hashes[m.batch_uuid] and m.sha256_hash is not None:
            m.capture_type = "batch_photo"
            m.capture_type_verified = True
            session.add(m)
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

    async with async_sessionmaker() as session:
        counts = await backfill(session, apply=args.apply)
        log.info(f"Backfill counts (apply={args.apply}): {counts}")

if __name__ == "__main__":
    asyncio.run(main())
