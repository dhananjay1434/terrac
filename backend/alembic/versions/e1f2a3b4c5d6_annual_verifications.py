"""create C9 annual_verifications table

Rainbow compliance C9: annual / per-verification project inputs, keyed by
(project_id, year) — methane rate (3 runs), PAH/heavy metals, biomass leakage,
conversion factor, dry bulk density, quality-oversight report.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annual_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(length=128), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("methane_rate_g_per_kg", sa.Float(), nullable=True),
        sa.Column("methane_run_count", sa.Integer(), nullable=True),
        sa.Column("conversion_factor", sa.Float(), nullable=True),
        sa.Column("pah_measured", sa.Boolean(), nullable=True),
        sa.Column("heavy_metals_measured", sa.Boolean(), nullable=True),
        sa.Column("leakage_assessment_done", sa.Boolean(), nullable=True),
        sa.Column("dry_bulk_density", sa.Float(), nullable=True),
        sa.Column("quality_oversight_sha256", sa.String(length=64), nullable=True),
        sa.Column("report_sha256", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "year", name="uq_annual_verif_project_year"),
    )
    op.create_index(
        "ix_annual_verifications_project_id", "annual_verifications", ["project_id"]
    )
    op.create_index("ix_annual_verifications_year", "annual_verifications", ["year"])


def downgrade() -> None:
    op.drop_index("ix_annual_verifications_year", table_name="annual_verifications")
    op.drop_index(
        "ix_annual_verifications_project_id", table_name="annual_verifications"
    )
    op.drop_table("annual_verifications")
