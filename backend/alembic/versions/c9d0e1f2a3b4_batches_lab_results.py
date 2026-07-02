"""batches: C7 per-batch lab results columns + organic_carbon_pct CHECK

Rainbow compliance C7: lab-verification data arrives on the admin channel.
organic_carbon_pct is credit-affecting (replaces the species CORG_TABLE constant
in the LCA); the rest are captured for verification / the 1000-year pathway.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK = "ck_batches_organic_carbon_pct_range"
_COND = (
    "organic_carbon_pct IS NULL "
    "OR (organic_carbon_pct > 0.0 AND organic_carbon_pct <= 1.0)"
)


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("organic_carbon_pct", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("biochar_moisture_samples_json", sa.Text(), nullable=True)
        )
        batch_op.add_column(sa.Column("dry_bulk_density", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("inertinite_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("residual_corg_pct", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("ro_measurements_count", sa.Integer(), nullable=True)
        )
        batch_op.create_check_constraint(_CK, _COND)


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_constraint(_CK, type_="check")
        batch_op.drop_column("ro_measurements_count")
        batch_op.drop_column("residual_corg_pct")
        batch_op.drop_column("inertinite_pct")
        batch_op.drop_column("dry_bulk_density")
        batch_op.drop_column("biochar_moisture_samples_json")
        batch_op.drop_column("organic_carbon_pct")
