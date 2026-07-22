"""create_bulk_density_tests_table

V8 Part 4 (F) — bulk-density volume→mass calibration. Purely additive: one
new table, no existing column touched.

Revision ID: 58f424124234
Revises: 8f0bb7661626
Create Date: 2026-07-22 16:31:30.033236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58f424124234'
down_revision: Union[str, None] = '8f0bb7661626'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bulk_density_tests",
        sa.Column("test_uuid", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(128), nullable=True),
        sa.Column("density_kg_per_l", sa.Float(), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mass_kg", sa.Float(), nullable=True),
        sa.Column("volume_l", sa.Float(), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_bulk_density_tests_project_id", "bulk_density_tests", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bulk_density_tests_project_id", table_name="bulk_density_tests")
    op.drop_table("bulk_density_tests")
