"""telemetry_v2: signed chunk store + unpacked point store (M2.1)

Additive new tables only. telemetry_chunks is the signed ingest unit with an
idempotency UNIQUE; telemetry_points is the queryable time-series with a
composite PK that doubles as point-level idempotency (audit A2). Plain tables on
both dialects here; Postgres partitioning of telemetry_points is deferred to the
M6.2 perf pass.

Revision ID: c9f1a3b5d7e2
Revises: b8e2d4f6a1c3
Create Date: 2026-07-27 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f1a3b5d7e2"
down_revision: Union[str, None] = "b8e2d4f6a1c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telemetry_chunks",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("t_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("t_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_period_s", sa.Float(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("signature", sa.String(length=128), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "batch_uuid", "channel", "t_start", "signature",
            name="uq_telemetry_chunks_idem",
        ),
    )
    op.create_index("ix_telemetry_chunks_batch_uuid", "telemetry_chunks", ["batch_uuid"])

    op.create_table(
        "telemetry_points",
        sa.Column("batch_uuid", sa.String(length=36), primary_key=True),
        sa.Column("channel", sa.String(length=16), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("value", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("telemetry_points")
    op.drop_index("ix_telemetry_chunks_batch_uuid", table_name="telemetry_chunks")
    op.drop_table("telemetry_chunks")
