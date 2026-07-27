"""Backfill batch_stage_events from existing evidence (M3.1).

Iterates batches WHERE no stage events exist, runs stage_projection on
available evidence (media + telemetry + dispatches + applications), and
inserts projected stage events. Idempotent: skips batches that already
have rows. Safe to re-run as new evidence arrives.

Usage:
    python tools/backfill_stages.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db import get_database_url
from models import (
    Base,
    Batch,
    BatchStageEvent,
    Dispatch,
    EndUseApplication,
    MediaFile,
    PyrolysisTelemetry,
)
from stage_projection import project_stages


async def backfill(dry_run: bool = False, limit: int | None = None) -> None:
    url = get_database_url()
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        # Find batches that have NO stage events yet
        has_events = select(BatchStageEvent.batch_uuid).distinct()
        q = (
            select(Batch.batch_uuid)
            .where(~Batch.batch_uuid.in_(has_events))
            .order_by(Batch.id)
        )
        if limit:
            q = q.limit(limit)

        batch_uuids = (await session.execute(q)).scalars().all()
        print(f"Found {len(batch_uuids)} batches without stage events")

        total_events = 0
        for i, uuid in enumerate(batch_uuids):
            # Load batch
            batch = (
                await session.execute(select(Batch).where(Batch.batch_uuid == uuid))
            ).scalar_one()

            # Load media
            media = (
                await session.execute(
                    select(MediaFile).where(MediaFile.batch_uuid == uuid)
                )
            ).scalars().all()

            # Load telemetry (legacy — for t_start/t_end via burn timestamps)
            tel = (
                await session.execute(
                    select(PyrolysisTelemetry).where(
                        PyrolysisTelemetry.batch_uuid == uuid
                    )
                )
            ).scalar_one_or_none()

            # Build telemetry dict for projection (use burn timestamps from batch)
            tel_dict = None
            if tel:
                import json
                try:
                    payload = json.loads(tel.payload_json) if tel.payload_json else {}
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                # Use batch harvest_timestamp as rough t_start if no better data
                tel_dict = {
                    "t_start": batch.harvest_timestamp,
                    "t_end": batch.received_at,
                }

            # Load dispatches
            dispatches = (
                await session.execute(
                    select(Dispatch).where(Dispatch.source_ref == uuid)
                )
            ).scalars().all()

            # Load end-use applications
            applications = (
                await session.execute(
                    select(EndUseApplication).where(
                        EndUseApplication.batch_uuid == uuid
                    )
                )
            ).scalars().all()

            # Project stages
            stages = project_stages(
                batch=batch,
                media=media,
                telemetry=tel_dict,
                dispatches=dispatches,
                applications=applications,
            )

            if stages:
                if dry_run:
                    print(
                        f"  [{i+1}/{len(batch_uuids)}] {uuid[:12]}… → "
                        f"{len(stages)} stages: {[s.stage for s in stages]}"
                    )
                else:
                    for s in stages:
                        session.add(
                            BatchStageEvent(
                                batch_uuid=uuid,
                                stage=s.stage,
                                started_at=s.started_at,
                                ended_at=s.ended_at,
                                source=s.source,
                            )
                        )
                total_events += len(stages)

            if (i + 1) % 100 == 0:
                print(f"  processed {i+1}/{len(batch_uuids)}…")
                if not dry_run:
                    await session.commit()

        if not dry_run:
            await session.commit()

        action = "would insert" if dry_run else "inserted"
        print(
            f"\nDone: {action} {total_events} stage events "
            f"across {len(batch_uuids)} batches"
        )

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Backfill batch stage events")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    parser.add_argument("--limit", type=int, default=None, help="Max batches to process")
    args = parser.parse_args()
    asyncio.run(backfill(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
