"""ADR-001 B4 steps 1–4 — assign batch-code ordinals to existing hierarchy.

Assigns org_ordinal (per-org network sequence) + network_code, site_ordinal
(per network), kiln_ordinal (per site), and a default country_code. Idempotent:
only fills NULLs, so it is safe to re-run weekly as ops maps more history.

Interpretation note (ADR B tension): org_ordinal is the network's sequence
WITHIN its org (1st network → 1 → code A001), which is the only reading that
satisfies BOTH unique(org_id, org_ordinal) and unique(org_id, network_code) and
still reproduces the golden `IN01A001` for the common one-network-per-org case.

SAFETY: `--remote <sqlite>` targets an explicit DB; the CLI otherwise reads
DATABASE_URL (the real DB in ops). Tests inject a scratch session directly.
"""
from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from models import Facility, Kiln, Network
from ordinals import allocate_ordinal, network_code_for


async def backfill_ordinals(
    session, *, dry_run: bool = False, default_country: str = "IN"
) -> dict:
    plan: dict[str, list] = {
        "networks": [],
        "facilities": [],
        "kilns": [],
        "country_defaults": [],
    }

    networks = (
        await session.execute(
            select(Network).order_by(Network.created_at, Network.network_id)
        )
    ).scalars().all()
    for n in networks:
        if n.org_ordinal is None and n.org_id:
            ordv = await allocate_ordinal(session, "network", n.org_id)
            n.org_ordinal = ordv
            n.network_code = network_code_for(ordv)
            plan["networks"].append((n.network_id, n.org_id, ordv, n.network_code))
        if not n.country_code:
            n.country_code = default_country
            plan["country_defaults"].append(n.network_id)
        await session.flush()  # so the next allocate_ordinal sees this max

    facilities = (
        await session.execute(
            select(Facility).order_by(Facility.created_at, Facility.facility_uuid)
        )
    ).scalars().all()
    for f in facilities:
        if f.site_ordinal is None and f.network_id:
            f.site_ordinal = await allocate_ordinal(session, "site", f.network_id)
            plan["facilities"].append((f.facility_uuid, f.network_id, f.site_ordinal))
            await session.flush()

    kilns = (
        await session.execute(
            select(Kiln).order_by(Kiln.registered_at, Kiln.kiln_id)
        )
    ).scalars().all()
    for k in kilns:
        if k.kiln_ordinal is None and k.site_id:
            k.kiln_ordinal = await allocate_ordinal(session, "kiln", k.site_id)
            plan["kilns"].append((k.kiln_id, k.site_id, k.kiln_ordinal))
            await session.flush()

    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return plan


async def _run(url: str, dry_run: bool) -> None:
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        smk = async_sessionmaker(engine, expire_on_commit=False)
        async with smk() as s:
            plan = await backfill_ordinals(s, dry_run=dry_run)
        tag = "DRY-RUN " if dry_run else ""
        print(
            f"{tag}ordinals: {len(plan['networks'])} networks, "
            f"{len(plan['facilities'])} sites, {len(plan['kilns'])} kilns, "
            f"{len(plan['country_defaults'])} country defaults"
        )
        for row in plan["networks"][:20]:
            print("  net", row)
    finally:
        await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description="Assign batch-code ordinals (ADR-001 B4.1-4).")
    ap.add_argument("--remote", help="explicit DATABASE_URL (sqlite for tests)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    url = args.remote or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("no DATABASE_URL and no --remote given")
    asyncio.run(_run(url, args.dry_run))


if __name__ == "__main__":
    main()
