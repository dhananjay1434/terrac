"""add_device_id_to_bulk_density_tests (PR-6.2 prerequisite)

Additive: a nullable device_id column. BulkDensityTest had no ownership
concept at all — the device-signed create endpoint (routers/density.py)
authenticates the caller but never persisted which device created a row,
so media (density_video) couldn't be ownership-checked. NULL for every
existing row (grandfather); the endpoint now sets it on new creates.

Revision ID: 25dde946cadb
Revises: 01601107f242
Create Date: 2026-07-23 13:15:52.581797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25dde946cadb'
down_revision: Union[str, None] = '01601107f242'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bulk_density_tests") as batch_op:
        batch_op.add_column(
            sa.Column("device_id", sa.String(length=255), nullable=True)
        )
    op.create_index(
        "ix_bulk_density_tests_device_id", "bulk_density_tests", ["device_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bulk_density_tests_device_id", table_name="bulk_density_tests")
    with op.batch_alter_table("bulk_density_tests") as batch_op:
        batch_op.drop_column("device_id")
