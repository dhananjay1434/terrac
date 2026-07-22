"""V8 Part 1.2 — real Alembic migration test for `9166634b188b`.

Tests:
- Alembic upgrade applies cleanly
- `source_parcels` table created with expected schema
- `batches.parcel_uuid` column added as nullable
- Alembic downgrade reverts cleanly
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
PREV_REVISION = "9f812d10294c"
THIS_REVISION = "9166634b188b"


def test_source_parcel_migration(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)

    db_url = f"sqlite+aiosqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # Upgrade to head
        command.upgrade(cfg, "head")

        sync_db_url = f"sqlite:///{path}"
        engine = create_engine(sync_db_url)
        inspector = inspect(engine)

        # Verify source_parcels table exists
        assert "source_parcels" in inspector.get_table_names()
        parcel_cols = {c["name"] for c in inspector.get_columns("source_parcels")}
        expected_cols = {
            "parcel_uuid",
            "project_id",
            "name",
            "boundary_geojson",
            "area_m2",
            "declared_area_acres",
            "bbox_min_lat",
            "bbox_min_lon",
            "bbox_max_lat",
            "bbox_max_lon",
            "boundary_method",
            "boundary_status",
            "created_by_user_id",
            "created_at",
        }
        assert expected_cols.issubset(parcel_cols)

        # Verify batches.parcel_uuid exists
        batch_cols = {c["name"]: c for c in inspector.get_columns("batches")}
        assert "parcel_uuid" in batch_cols
        assert batch_cols["parcel_uuid"]["nullable"] is True

        # Test downgrade to PREV_REVISION
        command.downgrade(cfg, PREV_REVISION)

        inspector_down = inspect(engine)
        assert "source_parcels" not in inspector_down.get_table_names()
        batch_cols_down = {c["name"] for c in inspector_down.get_columns("batches")}
        assert "parcel_uuid" not in batch_cols_down
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
