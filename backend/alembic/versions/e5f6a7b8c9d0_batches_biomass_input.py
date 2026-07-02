"""batches: add biomass_input_kg + biomass_measurement_method

Rainbow compliance C1: capture the biomass input amount (kg) and how it was
measured (direct_weigh | yield_conversion). Both nullable/additive.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("biomass_input_kg", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column("biomass_measurement_method", sa.String(length=32), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_column("biomass_measurement_method")
        batch_op.drop_column("biomass_input_kg")
