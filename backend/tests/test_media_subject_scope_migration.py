"""V8 deferred R1 — real Alembic migration test for `fbad0d51b1b1`.

Drives Alembic against a throwaway SQLite file: replays history up to the
pre-R1 HEAD (c8d9e0f1a2b3), inserts a media_files row exactly as an
already-deployed fleet would have (no subject_type/subject_uuid columns yet,
batch-scoped only), upgrades to this migration, and asserts the legacy row
survives untouched with NULL subject_type + the new columns/index exist, and
downgrade/re-upgrade round-trips cleanly.

Plain (non-async) test function: alembic's env.py calls asyncio.run()
internally, which cannot be invoked from inside an already-running event
loop — mirrors test_org_scoping_migration.py's convention.

Logging isolation (found while writing this test): backend/alembic/env.py
runs `logging.config.fileConfig(...)` on EVERY upgrade()/downgrade() call —
standard Alembic boilerplate — which reconfigures the ROOT logger from
alembic.ini and, by fileConfig's own default, disables/replaces any handlers
that were attached to it (including pytest's caplog capture handler). Left
unguarded, this silently breaks `caplog` for every test that runs AFTER this
one in the same process. `test_org_scoping_migration.py` has the identical
risk but has never tripped it, purely because its filename sorts after
"test_observability_gates.py" alphabetically. This test saves and restores
the root logger's handlers/level around every alembic call so it can't leak
that side effect regardless of file-collection order.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRE_MIGRATION_HEAD = "c8d9e0f1a2b3"
THIS_REVISION = "fbad0d51b1b1"


@contextmanager
def _preserve_logging_config():
    """See module docstring: alembic/env.py's fileConfig() call reconfigures
    logging as a side effect of running migrations. Two distinct things need
    restoring, both defaults of `logging.config.fileConfig`:
      1. The root logger's handlers/level get replaced from alembic.ini.
      2. `disable_existing_loggers=True` (fileConfig's default) sets
         `.disabled = True` on EVERY already-created logger not named in
         alembic.ini's [loggers] section (only root/sqlalchemy/alembic are
         named there) — including the "dmrv" logger `record_gate_rejection`
         uses, which is why its .warning() call silently no-ops afterwards
         with no error. Snapshot + restore both so this test can never leak
         either effect into later tests.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_disabled = {
        name: logger.disabled
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    try:
        yield
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
        for name, logger in logging.Logger.manager.loggerDict.items():
            if isinstance(logger, logging.Logger) and name in saved_disabled:
                logger.disabled = saved_disabled[name]


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


async def _insert_pre_migration_media_row(db_url: str) -> None:
    """A media_files row exactly as it would exist before this migration —
    no subject_type/subject_uuid columns in the schema yet."""
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO media_files "
                    "(batch_uuid, operation_id, file_path, sha256_hash, "
                    "capture_type_verified, uploaded_at) "
                    "VALUES (:batch_uuid, :op_id, :path, :sha, 0, :ts)"
                ),
                {
                    "batch_uuid": "11111111-1111-1111-1111-111111111111",
                    "op_id": "pre-migration-op-1",
                    "path": "evidence/pre-migration.jpg",
                    "sha": "a" * 64,
                    "ts": "2026-07-01T00:00:00+00:00",
                },
            )
    finally:
        await engine.dispose()


async def _column_exists(db_url: str, table: str, column: str) -> bool:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            return any(row[1] == column for row in result.fetchall())
    finally:
        await engine.dispose()


async def _legacy_row_survived(db_url: str) -> bool:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT batch_uuid, subject_type, subject_uuid FROM media_files "
                    "WHERE operation_id = 'pre-migration-op-1'"
                )
            )
            row = result.fetchone()
            return (
                row is not None
                and row[0] == "11111111-1111-1111-1111-111111111111"
                and row[1] is None
                and row[2] is None
            )
    finally:
        await engine.dispose()


async def _index_exists(db_url: str, index_name: str) -> bool:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name=:n"
                ),
                {"n": index_name},
            )
            return result.fetchone() is not None
    finally:
        await engine.dispose()


def test_subject_columns_added_and_legacy_row_untouched(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # alembic/sqlite creates it fresh
    db_url = f"sqlite+aiosqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    cfg = _alembic_config(db_url)
    try:
        with _preserve_logging_config():
            # 1) Replay history to the pre-R1 HEAD — no subject columns yet.
            command.upgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_type")) is False

        # 2) Seed a pre-existing batch-media row exactly as a live fleet would.
        asyncio.run(_insert_pre_migration_media_row(db_url))

        with _preserve_logging_config():
            # 3) Apply this migration.
            command.upgrade(cfg, THIS_REVISION)

        # 4) Columns + index exist; legacy row survives with NULL subject fields
        #    and its original batch_uuid untouched (grandfathered).
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_type")) is True
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_uuid")) is True
        assert asyncio.run(_index_exists(db_url, "ix_media_files_subject_uuid")) is True
        assert asyncio.run(_legacy_row_survived(db_url)) is True

        with _preserve_logging_config():
            # 5) downgrade() must cleanly drop the index + both columns.
            command.downgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_type")) is False
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_uuid")) is False

        with _preserve_logging_config():
            # 6) Re-upgrading reproduces the same schema (upgrade doesn't depend on
            #    migration-run history).
            command.upgrade(cfg, THIS_REVISION)
        assert asyncio.run(_column_exists(db_url, "media_files", "subject_type")) is True
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
