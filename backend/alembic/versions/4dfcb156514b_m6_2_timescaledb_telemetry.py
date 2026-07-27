"""m6_2_timescaledb_telemetry

Revision ID: 4dfcb156514b
Revises: 188d8c9bd89a
Create Date: 2026-07-27 14:41:18.011924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4dfcb156514b'
down_revision: Union[str, None] = '188d8c9bd89a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Check if TimescaleDB is available on this Postgres server
        has_timescale = bind.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
        ).scalar()

        if has_timescale:
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            op.execute("SELECT create_hypertable('telemetry_points', 'ts', if_not_exists => TRUE);")
            print("Successfully converted telemetry_points to TimescaleDB hypertable.")
        else:
            print("Warning: TimescaleDB extension not available on this Postgres server. Gracefully degrading to standard tables.")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # To reverse a hypertable, we would normally migrate data back or drop the hypertable.
        # However, dropping the extension removes the hypertable constraint but keeps the data table in a regular form.
        # For a safer downgrade that doesn't delete telemetry, we leave it as is, or just drop the extension if it's safe.
        pass
