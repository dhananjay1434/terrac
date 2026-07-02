"""create moisture_readings table

Rainbow compliance C2: one moisture-meter reading per row (many per batch;
≥1 per 100 kg, min 10). batch_uuid is indexed but NOT unique.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moisture_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reading_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_moisture_readings_reading_uuid",
        "moisture_readings",
        ["reading_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_moisture_readings_batch_uuid", "moisture_readings", ["batch_uuid"]
    )


def downgrade() -> None:
    op.drop_index("ix_moisture_readings_batch_uuid", table_name="moisture_readings")
    op.drop_index("ix_moisture_readings_reading_uuid", table_name="moisture_readings")
    op.drop_table("moisture_readings")
