"""batch_stage_events: custody-chain timeline events (M3.1)

Additive new table only. Each batch has at most one row per stage
(UNIQUE constraint). The stage whitelist is CHECK-enforced. Source
tracks provenance: 'projected' for backfilled data, 'device'/'edge'/
'admin' for forward-path writes.

Revision ID: d1e2f3a4b5c6
Revises: c9f1a3b5d7e2
Create Date: 2026-07-27 18:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9f1a3b5d7e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGE_WHITELIST = (
    "sourcing", "moisture", "loading", "firing", "biochar_addition",
    "pre_quenching", "quenching", "yield", "mixing", "packaging",
    "dispatch", "application", "lab",
)

_SOURCE_WHITELIST = ("device", "edge", "projected", "admin")


def upgrade() -> None:
    op.create_table(
        "batch_stage_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("batch_uuid", "stage", name="uq_stage_events_batch_stage"),
        sa.CheckConstraint(
            f"stage IN ({', '.join(repr(s) for s in _STAGE_WHITELIST)})",
            name="ck_stage_events_stage",
        ),
        sa.CheckConstraint(
            f"source IN ({', '.join(repr(s) for s in _SOURCE_WHITELIST)})",
            name="ck_stage_events_source",
        ),
    )
    op.create_index("ix_stage_events_batch_uuid", "batch_stage_events", ["batch_uuid"])


def downgrade() -> None:
    op.drop_index("ix_stage_events_batch_uuid", table_name="batch_stage_events")
    op.drop_table("batch_stage_events")
