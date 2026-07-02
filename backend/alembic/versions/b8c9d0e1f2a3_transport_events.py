"""create transport_events table

Rainbow compliance C6: one transport event per row (many per batch).
event_uuid is unique; batch_uuid is indexed but NOT unique.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transport_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_transport_events_event_uuid",
        "transport_events",
        ["event_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_transport_events_batch_uuid",
        "transport_events",
        ["batch_uuid"],
    )


def downgrade() -> None:
    op.drop_index("ix_transport_events_batch_uuid", table_name="transport_events")
    op.drop_index("ix_transport_events_event_uuid", table_name="transport_events")
    op.drop_table("transport_events")
