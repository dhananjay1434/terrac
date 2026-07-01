"""batches: add lab_h_corg + provisional_reasons

Phase 7-R: credit inputs are corroborated server-side and the batch stays
PROVISIONAL until corroborated. `lab_h_corg` persists a lab-measured H:Corg so a
recompute triggered by a later evidence stream does not lose it; `provisional_reasons`
records why a batch is not yet issuable (audit trail). Both nullable.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("lab_h_corg", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("provisional_reasons", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_column("provisional_reasons")
        batch_op.drop_column("lab_h_corg")
