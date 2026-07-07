"""batches: add project_id + scale_id linkage (Rainbow T1.1)

Resolves the project-scoped C10 gates (scale calibration, annual methane, PAH)
that were dormant for lack of a batch->project/scale linkage. Both columns are
nullable/additive; legacy batches keep NULL and the gates stay inert for them.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(
            sa.Column("project_id", sa.String(length=128), nullable=True)
        )
        batch_op.add_column(sa.Column("scale_id", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_batches_project_id", ["project_id"])
        batch_op.create_index("ix_batches_scale_id", ["scale_id"])


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_index("ix_batches_scale_id")
        batch_op.drop_index("ix_batches_project_id")
        batch_op.drop_column("scale_id")
        batch_op.drop_column("project_id")
