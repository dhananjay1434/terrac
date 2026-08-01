"""Adds multi-channel burn telemetry (T1-T4 thermocouples + LOAD) to a
representative subset of already-seeded demo batches, so the portal's
ThermalMapChart / LoadTelemetryChart (which read from TelemetryPoint via
GET /api/v1/portal/batches/{uuid}/telemetry2) have real data to render.

Idempotent-safe like seed_demo_rich.py: only touches batches that don't
already have TelemetryPoint rows, and never modifies/deletes existing rows.

Run from backend/ with DATABASE_URL in env (loaded from .env by default, or
pass --remote <url> to target a specific database explicitly).
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import random
from datetime import timedelta, timezone

from dotenv import load_dotenv

BATCH_LIMIT = 12  # representative subset, not the whole table
# Cadence of synthesized points. Must stay under the backend's gap-detection
# threshold (telemetry_routes._GAP_THRESHOLD_MS = 60s, tuned for a real 10s
# sample rate) — a coarser cadence would have every step boundary misread as
# a sensor dropout, since all 5 channels share each timestamp and the merged
# all_ts diff jumps by the full step at every boundary.
STEP_SECONDS = 30
BURN_HOURS = 3

# Per-channel peak temp + timing offset so the four thermocouples are
# visibly distinct on ThermalMapChart (T4 is placed "bottom" per the portal's
# PLACEMENT map — runs a bit hotter/faster than the three "side" probes).
_CHANNEL_PROFILE = {
    "T1": {"peak": 610.0, "peak_frac": 0.45},
    "T2": {"peak": 635.0, "peak_frac": 0.50},
    "T3": {"peak": 590.0, "peak_frac": 0.55},
    "T4": {"peak": 665.0, "peak_frac": 0.40},
}


def _burn_curve(peak: float, peak_frac: float, frac: float, rng: random.Random) -> float:
    """Ambient -> peak -> cool-down, as a fraction [0,1] of the burn duration."""
    ambient = 27.0
    if frac <= peak_frac:
        base = ambient + (peak - ambient) * (frac / peak_frac)
    else:
        tail = (frac - peak_frac) / (1 - peak_frac)
        base = peak - (peak - 140.0) * tail
    return round(base + rng.uniform(-4.0, 4.0), 1)


def _load_curve(start_kg: float, end_kg: float, frac: float, rng: random.Random) -> float:
    base = start_kg - (start_kg - end_kg) * frac
    return round(max(end_kg, base + rng.uniform(-0.4, 0.4)), 2)


async def main() -> None:
    from sqlalchemy import select

    from db import engine
    from models import Batch, TelemetryPoint

    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        candidates = (
            await s.execute(
                select(Batch)
                .order_by(Batch.received_at.desc())
                .limit(BATCH_LIMIT * 3)  # over-fetch; some may already have telemetry
            )
        ).scalars().all()

        seeded = 0
        for batch in candidates:
            if seeded >= BATCH_LIMIT:
                break
            existing = (
                await s.execute(
                    select(TelemetryPoint.batch_uuid)
                    .where(TelemetryPoint.batch_uuid == batch.batch_uuid)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue  # idempotent: already has telemetry, skip

            rng = random.Random(batch.batch_uuid)  # stable per-batch synthetic data
            burn_end = batch.received_at
            burn_start = burn_end - timedelta(hours=BURN_HOURS)
            n_steps = int((BURN_HOURS * 3600) / STEP_SECONDS) + 1

            # NOT batch.biomass_input_kg — that field is scaled up (DEMO_SCALE=50x
            # in seed_demo_rich.py) to keep dashboard credit totals legible, and
            # would put an unrealistic ~20,000 kg on a single kiln's load cell.
            # LOAD is a physical scale reading, so it gets its own plausible range.
            start_kg = rng.uniform(80.0, 150.0)
            end_kg = max(15.0, start_kg * rng.uniform(0.22, 0.32))

            rows: list[dict] = []
            for i in range(n_steps):
                frac = i / (n_steps - 1)
                ts = burn_start + timedelta(seconds=i * STEP_SECONDS)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                for channel, prof in _CHANNEL_PROFILE.items():
                    rows.append(
                        {
                            "batch_uuid": batch.batch_uuid,
                            "channel": channel,
                            "ts": ts,
                            "value": _burn_curve(prof["peak"], prof["peak_frac"], frac, rng),
                        }
                    )
                rows.append(
                    {
                        "batch_uuid": batch.batch_uuid,
                        "channel": "LOAD",
                        "ts": ts,
                        "value": _load_curve(start_kg, end_kg, frac, rng),
                    }
                )

            await s.execute(TelemetryPoint.__table__.insert(), rows)
            seeded += 1
            print(f"  telemetry seeded: {batch.batch_code or batch.batch_uuid[:8]} ({len(rows)} points)")

        await s.commit()
        print(f"Done — {seeded} batch(es) newly got T1-T4 + LOAD telemetry.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add multi-channel demo burn telemetry.")
    parser.add_argument("--remote", type=str, help="Optional DATABASE_URL to target explicitly.")
    args = parser.parse_args()

    if args.remote:
        print(f"Seeding target database: {args.remote.split('@')[-1]}")
        os.environ["DATABASE_URL"] = args.remote
    else:
        load_dotenv()
        print("Seeding database from .env / current DATABASE_URL")

    asyncio.run(main())
