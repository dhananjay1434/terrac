"""chunk idempotency keyed on session_uuid, not nullable batch_uuid

M2.9 made telemetry_chunks.batch_uuid nullable so chunks can arrive before they
are bound to a batch. Because NULL != NULL in SQL, the old UNIQUE could never
fire for unbound chunks and retried uploads inserted duplicates. session_uuid is
always present, so the idempotency key moves to it.

Revision ID: e4a1c7b2f9d5
Revises: 4dfcb156514b
Create Date: 2026-07-27 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e4a1c7b2f9d5"
down_revision: Union[str, None] = "4dfcb156514b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("telemetry_chunks") as batch_op:
        batch_op.drop_constraint("uq_telemetry_chunks_idem", type_="unique")
        batch_op.create_unique_constraint(
            "uq_telemetry_chunks_idem",
            ["session_uuid", "channel", "t_start", "signature"],
        )


def downgrade() -> None:
    with op.batch_alter_table("telemetry_chunks") as batch_op:
        batch_op.drop_constraint("uq_telemetry_chunks_idem", type_="unique")
        batch_op.create_unique_constraint(
            "uq_telemetry_chunks_idem",
            ["batch_uuid", "channel", "t_start", "signature"],
        )
