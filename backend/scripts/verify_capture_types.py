"""Read-only audit of media_files.capture_type classification. NEVER writes.

Companion to scripts/backfill_media_capture_types.py: run this before and after
a backfill to see exactly what is (still) unclassified and why. Safe against any
database — it only SELECTs.

Usage (DATABASE_URL must be set — local sqlite or the remote URL):
    DATABASE_URL='sqlite+aiosqlite:///./dmrv.db' python scripts/verify_capture_types.py
    DATABASE_URL='<remote-url>' python scripts/verify_capture_types.py <batch_uuid>

Without a batch_uuid: prints the global capture_type histogram + the count of
rows still NULL. With a batch_uuid: also breaks that batch's media down and
cross-references each photo against moisture_readings / composite_pile_samples,
so a still-NULL row's real kind (or genuine unknown) is visible at a glance.
"""
import asyncio
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _shas(rows):
    out = {}
    for (pj,) in rows:
        try:
            d = json.loads(pj)
        except Exception:
            continue
        s = d.get("sha256_hash")
        if s:
            out[str(s).lower()] = d
    return out


async def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: set DATABASE_URL (local sqlite or the remote URL) first.", file=sys.stderr)
        return 2
    batch = sys.argv[1] if len(sys.argv) > 1 else None

    eng = create_async_engine(url)
    try:
        async with eng.connect() as c:
            r = await c.execute(
                text(
                    "SELECT capture_type, count(*) FROM media_files "
                    "GROUP BY capture_type ORDER BY 2 DESC"
                )
            )
            print("=== capture_type histogram (all batches) ===")
            for ct, n in r.fetchall():
                print(f"  {ct if ct is not None else 'NULL':20} {n}")
            r = await c.execute(text("SELECT count(*) FROM media_files WHERE capture_type IS NULL"))
            print("remaining NULL capture_type:", r.fetchone()[0])

            if not batch:
                print("\n(pass a batch_uuid as the first argument for a per-batch breakdown)")
                return 0

            print(f"\n=== batch {batch} ===")
            mr = _shas(
                (
                    await c.execute(
                        text("SELECT payload_json FROM moisture_readings WHERE batch_uuid=:b"),
                        {"b": batch},
                    )
                ).fetchall()
            )
            cp = _shas(
                (
                    await c.execute(
                        text("SELECT payload_json FROM composite_pile_samples WHERE batch_uuid=:b"),
                        {"b": batch},
                    )
                ).fetchall()
            )
            r = await c.execute(
                text(
                    "SELECT sha256_hash, capture_type FROM media_files "
                    "WHERE batch_uuid=:b ORDER BY uploaded_at"
                ),
                {"b": batch},
            )
            for sha, ct in r.fetchall():
                s = (sha or "").lower()
                matches = (
                    "moisture-record" if s in mr else ("composite-record" if s in cp else "-")
                )
                print(f"  {s[:12]}  capture_type={ct if ct else 'NULL':16}  matches:{matches}")
        return 0
    finally:
        await eng.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
