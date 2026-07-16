import argparse
import asyncio
import logging

from sqlalchemy import select

from db import async_sessionmaker
from models import MediaFile, PyrolysisTelemetry, Batch
from services.evidence import label_media_from_telemetry

log = logging.getLogger("dmrv.backfill")
logging.basicConfig(level=logging.INFO)

async def backfill(session, apply: bool = False) -> dict:
    counts = {"telemetry": 0, "lab_certificate": 0, "batch_photo": 0, "unchanged": 0}

    # 1. Telemetry rule
    # Iterate all telemetry and call label_media_from_telemetry
    tels = (await session.execute(select(PyrolysisTelemetry))).scalars().all()
    for t in tels:
        try:
            import json
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

    # 3. Batch anchor photo
    # rows whose sha256_hash equals their batch's batches.sha256_hash -> capture_type="batch_photo", verified True
    all_medias = (await session.execute(
        select(MediaFile).where(MediaFile.capture_type_verified == False)
    )).scalars().all()

    # Pre-fetch batches for quick lookup (if many, might need join, but small dataset is fine)
    batches = (await session.execute(select(Batch.batch_uuid, Batch.sha256_hash))).all()
    batch_hashes = {b.batch_uuid: b.sha256_hash for b in batches}

    for m in all_medias:
        if not m.capture_type_verified and m.batch_uuid in batch_hashes and m.sha256_hash == batch_hashes[m.batch_uuid] and m.sha256_hash is not None:
            m.capture_type = "batch_photo"
            m.capture_type_verified = True
            session.add(m)
            counts["batch_photo"] += 1
        elif not m.capture_type_verified:
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
