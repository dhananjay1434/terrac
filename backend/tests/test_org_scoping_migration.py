"""V8 Part 5 (D) — real Alembic migration test for `b7c1d2e3f4a5`.

Drives Alembic against a throwaway SQLite file (not just ORM
`Base.metadata.create_all`): replays history up to the pre-Part-5 HEAD
(58f424124234), inserts a portal_users row the way an already-deployed
fleet would have (no org_id column, role CHECK not yet widened), upgrades to
this migration, and asserts the column exists + the CHECK constraint accepts
'org_admin' + downgrade/re-upgrade round-trips cleanly.

Plain (non-async) test function: alembic's env.py calls asyncio.run()
internally, which cannot be invoked from inside an already-running event
loop — mirrors test_project_entity_migration.py's convention.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from alembic.config import Config
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
PRE_MIGRATION_HEAD = "58f424124234"
THIS_REVISION = "b7c1d2e3f4a5"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


async def _insert_pre_migration_user(db_url: str) -> None:
    """A portal_users row exactly as it would exist before this migration —
    no org_id column in the schema yet, so this can't reference it."""
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO portal_users "
                    "(email, password_hash, role, disabled, created_at) "
                    "VALUES (:email, :ph, :role, 0, :ts)"
                ),
                {
                    "email": "pre-migration-admin@test.local",
                    "ph": "argon2-hash-placeholder",
                    "role": "admin",
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


async def _try_insert_org_admin(db_url: str) -> bool:
    """Attempt to insert a role='org_admin' row; return True if the CHECK
    constraint allowed it (post-migration expectation), False if rejected."""
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            try:
                await conn.execute(
                    text(
                        "INSERT INTO portal_users "
                        "(email, password_hash, role, org_id, disabled, created_at) "
                        "VALUES (:email, :ph, 'org_admin', :org, 0, :ts)"
                    ),
                    {
                        "email": "org-admin@test.local",
                        "ph": "argon2-hash-placeholder",
                        "org": "org-a",
                        "ts": "2026-07-22T00:00:00+00:00",
                    },
                )
                return True
            except IntegrityError:
                return False
    finally:
        await engine.dispose()


async def _delete_org_admin_row(db_url: str) -> None:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM portal_users WHERE role = 'org_admin'")
            )
    finally:
        await engine.dispose()


async def _existing_user_survived(db_url: str) -> bool:
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT role, org_id FROM portal_users "
                    "WHERE email = 'pre-migration-admin@test.local'"
                )
            )
            row = result.fetchone()
            return row is not None and row[0] == "admin" and row[1] is None
    finally:
        await engine.dispose()


def test_org_id_column_and_widened_role_check(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # alembic/sqlite creates it fresh
    db_url = f"sqlite+aiosqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    cfg = _alembic_config(db_url)
    try:
        # 1) Replay history to the pre-Part-5 HEAD — no org_id column yet.
        command.upgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_column_exists(db_url, "portal_users", "org_id")) is False

        # 2) Seed a pre-existing user exactly as a live deployment would have.
        asyncio.run(_insert_pre_migration_user(db_url))

        # 3) Apply this migration.
        command.upgrade(cfg, THIS_REVISION)

        # 4) Column exists; pre-existing row is untouched (role unchanged,
        #    org_id defaults to NULL — unscoped, sees everything as before).
        assert asyncio.run(_column_exists(db_url, "portal_users", "org_id")) is True
        assert asyncio.run(_existing_user_survived(db_url)) is True

        # 5) The widened CHECK now accepts 'org_admin'.
        assert asyncio.run(_try_insert_org_admin(db_url)) is True

        # 6) downgrade() must cleanly drop the column and revert the CHECK
        #    (regression guard: a broken downgrade is a broken rollback plan).
        #    An 'org_admin' row existing at downgrade time would correctly
        #    violate the OLD (narrower) constraint the batch-recreate copy
        #    re-checks against — remove it first, same as an operator would
        #    have to migrate/reassign that data before rolling back.
        asyncio.run(_delete_org_admin_row(db_url))
        command.downgrade(cfg, PRE_MIGRATION_HEAD)
        assert asyncio.run(_column_exists(db_url, "portal_users", "org_id")) is False

        # 7) Re-upgrading reproduces the same widened CHECK (upgrade doesn't
        #    depend on migration-run history).
        command.upgrade(cfg, THIS_REVISION)
        assert asyncio.run(_try_insert_org_admin(db_url)) is True
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
