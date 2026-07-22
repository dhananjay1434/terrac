"""V8 Part 0.2 — real Alembic migration test for `1a901336bb62`.

Unlike test_project_entity.py (which uses Base.metadata.create_all, the
fast path the rest of the suite uses), this test actually DRIVES ALEMBIC
against a throwaway SQLite file: replays history up to the pre-Part-0.2 HEAD
(d6e7f8a9bac1), inserts rows the way an already-deployed fleet would have
(no `projects` table exists yet), then upgrades to this migration and asserts
the backfill is complete, non-duplicating, and that downgrade+re-upgrade
round-trips cleanly.

Plain (non-async) test functions: alembic's env.py calls asyncio.run()
internally (see backend/alembic/env.py), which cannot be invoked from inside
an already-running event loop — so these tests must not be pytest-asyncio
coroutines themselves.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRE_MIGRATION_HEAD = "d6e7f8a9bac1"
THIS_REVISION = "1a901336bb62"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # env.py reads DATABASE_URL from the environment (see alembic/env.py); the
    # sqlalchemy.url set here is a fallback env.py overrides if that's present.
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


async def _insert_pre_migration_data(db_url: str) -> None:
    """Insert batches/annual_verifications rows exactly as an already-deployed
    fleet would have, BEFORE the `projects` table exists. Uses the Batch/
    AnnualVerification mapped Table objects (not raw textual SQL) so Python-
    side column defaults (wet_yield_kg, status, etc.) are applied — the
    `batches` table's schema is untouched by this migration, so this
    accurately represents pre-migration data.
    """
    from models import Batch, AnnualVerification

    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                Batch.__table__.insert(),
                [
                    {
                        "batch_uuid": "11111111-1111-1111-1111-111111111111",
                        "operation_id": "op-1",
                        "feedstock_species": "Lantana_camara",
                        "harvest_timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                        "moisture_percent": 12.0,
                        "harvest_uptime_seconds": 100,
                        "project_id": "proj-alpha",
                    },
                    {
                        "batch_uuid": "22222222-2222-2222-2222-222222222222",
                        "operation_id": "op-2",
                        "feedstock_species": "Lantana_camara",
                        "harvest_timestamp": datetime(2026, 1, 2, tzinfo=timezone.utc),
                        "moisture_percent": 13.0,
                        "harvest_uptime_seconds": 100,
                        # Second batch on the SAME project — backfill must not
                        # create a duplicate `projects` row for proj-alpha.
                        "project_id": "proj-alpha",
                    },
                    {
                        "batch_uuid": "33333333-3333-3333-3333-333333333333",
                        "operation_id": "op-3",
                        "feedstock_species": "Lantana_camara",
                        "harvest_timestamp": datetime(2026, 1, 3, tzinfo=timezone.utc),
                        "moisture_percent": 14.0,
                        "harvest_uptime_seconds": 100,
                        "project_id": "proj-beta",
                    },
                    {
                        "batch_uuid": "44444444-4444-4444-4444-444444444444",
                        "operation_id": "op-4",
                        "feedstock_species": "Lantana_camara",
                        "harvest_timestamp": datetime(2026, 1, 4, tzinfo=timezone.utc),
                        "moisture_percent": 15.0,
                        "harvest_uptime_seconds": 100,
                        "project_id": None,  # grandfathered: no project at all
                    },
                ],
            )
            await conn.execute(
                AnnualVerification.__table__.insert(),
                [
                    {
                        "project_id": "proj-gamma",  # only referenced here, not in batches
                        "year": 2026,
                        "payload_json": "{}",
                    }
                ],
            )
    finally:
        await engine.dispose()


async def _query_project_ids(db_url: str) -> set[str]:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT project_id FROM projects"))
            return {row[0] for row in result.fetchall()}
    finally:
        await engine.dispose()


async def _table_exists(db_url: str, table_name: str) -> bool:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": table_name},
            )
            return result.first() is not None
    finally:
        await engine.dispose()


async def _rerun_backfill_sql_directly(db_url: str) -> None:
    """Executes the exact idempotent backfill statement the migration uses,
    a second time, directly against an already-migrated DB — proving the
    'safe to re-run' claim in the migration's docstring without relying on
    Alembic's revision bookkeeping (which would no-op a second `upgrade`)."""
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            for source_table in ("batches", "annual_verifications"):
                await conn.execute(
                    text(
                        f"""
                        INSERT INTO projects (project_id, name, status, created_at)
                        SELECT DISTINCT project_id, project_id, 'active', CURRENT_TIMESTAMP
                        FROM {source_table}
                        WHERE project_id IS NOT NULL
                          AND project_id NOT IN (SELECT project_id FROM projects)
                        """
                    )
                )
    finally:
        await engine.dispose()


def test_backfill_covers_all_distinct_project_ids_with_zero_orphans(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # alembic/sqlite creates it fresh
    db_url = f"sqlite+aiosqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    cfg = _alembic_config(db_url)
    try:
        # 1) Replay history up to the pre-Part-0.2 HEAD — the schema an
        #    already-deployed fleet actually has today, no `projects` table.
        command.upgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_table_exists(db_url, "projects")) is False

        # 2) Seed data exactly as a live fleet would have it.
        asyncio.run(_insert_pre_migration_data(db_url))

        # 3) Apply this migration.
        command.upgrade(cfg, THIS_REVISION)

        # 4) Backfill assertions: every distinct non-null project_id from
        #    BOTH source tables got exactly one row; the null-project batch
        #    contributed nothing (no fabricated project).
        ids = asyncio.run(_query_project_ids(db_url))
        assert ids == {"proj-alpha", "proj-beta", "proj-gamma"}

        # 5) Idempotency: re-running the backfill SQL against the now-migrated
        #    DB must not create duplicates or error.
        asyncio.run(_rerun_backfill_sql_directly(db_url))
        ids_after_rerun = asyncio.run(_query_project_ids(db_url))
        assert ids_after_rerun == ids

        # 6) downgrade() must cleanly remove the table (regression guard: a
        #    broken downgrade is a broken rollback plan in production).
        command.downgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_table_exists(db_url, "projects")) is False

        # 7) Re-upgrading from the downgraded state must reproduce the same
        #    backfill (proves upgrade doesn't depend on migration-run history).
        command.upgrade(cfg, THIS_REVISION)
        ids_after_roundtrip = asyncio.run(_query_project_ids(db_url))
        assert ids_after_roundtrip == ids
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
