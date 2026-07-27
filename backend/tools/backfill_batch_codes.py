"""M1.3 (ADR-001 B4 step 5) — generate batch_code for batches with complete,
ordinal-assigned lineage.

Lineage: batch → its telemetry `kiln_id` (credit_engine.py:410 semantics) →
Kiln → Facility(site) → Network. Every link must be present AND ordinal-assigned
(run backfill_ordinals first); any gap → batch_code stays NULL (audit A3:
NULL-until-lineage-known, portal falls back to short-UUID). Idempotent — only
touches NULL codes. Sequence is per (kiln, IST-day), ordered by received_at,id.

SAFETY: `--remote <sqlite>` targets an explicit DB; tests inject a scratch
session directly. Never reads .env implicitly.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from batch_codes import make_batch_code, slot_for
from models import Batch, Facility, Kiln, Network, PyrolysisTelemetry

_IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist(dt):
    return dt.astimezone(_IST) if dt.tzinfo else dt


async def _kiln_id_for(session, batch_uuid: str):
    raw = (
        await session.execute(
            select(PyrolysisTelemetry.payload_json).where(
                PyrolysisTelemetry.batch_uuid == batch_uuid
            )
        )
    ).scalar_one_or_none()
    if not raw:
        return None
    try:
        return (json.loads(raw) or {}).get("kiln_id")
    except (ValueError, TypeError):
        return None


async def backfill_batch_codes(session, *, dry_run: bool = False) -> dict:
    result = {"coded": [], "skipped_incomplete": 0}
    batches = (
        await session.execute(
            select(Batch)
            .where(Batch.batch_code.is_(None))
            .order_by(Batch.received_at, Batch.id)
        )
    ).scalars().all()

    seq_counter: dict[tuple, int] = {}  # (kiln_id, ist-date) → running seq this run

    for b in batches:
        if b.received_at is None:
            result["skipped_incomplete"] += 1
            continue
        kiln_id = await _kiln_id_for(session, b.batch_uuid)
        if not kiln_id:
            result["skipped_incomplete"] += 1
            continue
        kiln = (
            await session.execute(select(Kiln).where(Kiln.kiln_id == kiln_id))
        ).scalar_one_or_none()
        if kiln is None or kiln.kiln_ordinal is None or not kiln.site_id:
            result["skipped_incomplete"] += 1
            continue
        fac = (
            await session.execute(
                select(Facility).where(Facility.facility_uuid == kiln.site_id)
            )
        ).scalar_one_or_none()
        if fac is None or fac.site_ordinal is None or not fac.network_id:
            result["skipped_incomplete"] += 1
            continue
        net = (
            await session.execute(
                select(Network).where(Network.network_id == fac.network_id)
            )
        ).scalar_one_or_none()
        if (
            net is None
            or net.org_ordinal is None
            or not net.network_code
            or not net.country_code
        ):
            result["skipped_incomplete"] += 1
            continue

        day = _to_ist(b.received_at)
        key = (kiln_id, day.date())
        seq_counter[key] = seq_counter.get(key, 0) + 1
        try:
            code = make_batch_code(
                country=net.country_code,
                org_num=net.org_ordinal,
                network_code=net.network_code,
                site_num=fac.site_ordinal,
                slot_num=slot_for(b.received_at),
                kiln_num=kiln.kiln_ordinal,
                day=day,
                seq=seq_counter[key],
            )
        except ValueError:
            result["skipped_incomplete"] += 1
            continue
        b.batch_code = code
        b.network_id = net.network_id  # populate the hierarchy links too
        b.site_id = fac.facility_uuid
        result["coded"].append((b.batch_uuid, code))

    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return result


async def _run(url: str, dry_run: bool) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        smk = async_sessionmaker(engine, expire_on_commit=False)
        async with smk() as s:
            res = await backfill_batch_codes(s, dry_run=dry_run)
        tag = "DRY-RUN " if dry_run else ""
        print(f"{tag}coded {len(res['coded'])}, left NULL {res['skipped_incomplete']}")
        for row in res["coded"][:20]:
            print("  ", row)
    finally:
        await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate batch_code from lineage (ADR-001 B4.5).")
    ap.add_argument("--remote", help="explicit DATABASE_URL (sqlite for tests)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    url = args.remote or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("no DATABASE_URL and no --remote given")
    asyncio.run(_run(url, args.dry_run))


if __name__ == "__main__":
    main()
