#!/usr/bin/env python3
"""P3.5 — verify a restored dMRV instance.

Run this against a freshly-restored database (+ its media store) to confirm the
restore is intact before cutting traffic to it:

  1. counts rows in the batch + evidence + media tables (a near-empty restore is
     a red flag),
  2. spot-verifies N media objects: reads the bytes back through the storage
     abstraction and checks sha256 == media_files.sha256_hash (proves the DB and
     the object store were restored to a consistent point).

Exits non-zero on any hash mismatch, unreadable sampled object, or an empty
batch table.

Usage:
  DMRV_MEDIA_BACKEND=s3 DMRV_MEDIA_BUCKET=... DMRV_S3_ENDPOINT=... \
  python scripts/verify_restore.py \
      --database-url postgresql+asyncpg://USER:PW@HOST:5432/dmrv --media-sample 20
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import (  # noqa: E402
    Batch,
    CompositePileSample,
    EndUseApplication,
    MediaFile,
    MoistureReading,
    PyrolysisTelemetry,
    YieldMetrics,
)
from storage import get_storage  # noqa: E402

_COUNT_TABLES = {
    "batches": Batch,
    "telemetry": PyrolysisTelemetry,
    "yield": YieldMetrics,
    "moisture": MoistureReading,
    "application": EndUseApplication,
    "composite_sample": CompositePileSample,
    "media_files": MediaFile,
}


async def _count(session, model) -> int:
    return int((await session.execute(select(func.count()).select_from(model))).scalar() or 0)


async def main() -> int:
    ap = argparse.ArgumentParser(description="verify a restored dMRV instance")
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    ap.add_argument("--media-sample", type=int, default=20)
    args = ap.parse_args()
    if not args.database_url:
        print("ERROR: --database-url (or DATABASE_URL) required")
        return 2

    engine = create_async_engine(args.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    ok = True
    try:
        async with Session() as session:
            print("=== row counts ===")
            counts = {}
            for label, model in _COUNT_TABLES.items():
                counts[label] = await _count(session, model)
                print(f"  {label:<18}{counts[label]:>10}")

            if counts["batches"] == 0:
                print("FAIL: zero batches — restore looks empty")
                ok = False

            # Spot-verify media object integrity against the store.
            rows = (
                (
                    await session.execute(
                        select(MediaFile).limit(args.media_sample)
                    )
                )
                .scalars()
                .all()
            )
            print(f"\n=== media integrity ({len(rows)} sampled) ===")
            storage = get_storage()
            checked = mismatched = missing = 0
            for row in rows:
                try:
                    data = b"".join(storage.open_stream(row.file_path))
                except (FileNotFoundError, ValueError):
                    missing += 1
                    ok = False
                    print(f"  MISSING  {row.operation_id}  ({row.file_path})")
                    continue
                digest = hashlib.sha256(data).hexdigest()
                checked += 1
                if digest.lower() != (row.sha256_hash or "").lower():
                    mismatched += 1
                    ok = False
                    print(f"  MISMATCH {row.operation_id}  db={row.sha256_hash[:12]}… got={digest[:12]}…")
            print(
                f"  verified={checked} mismatched={mismatched} missing={missing}"
            )
    finally:
        await engine.dispose()

    print("\nRESTORE OK" if ok else "\nRESTORE VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
