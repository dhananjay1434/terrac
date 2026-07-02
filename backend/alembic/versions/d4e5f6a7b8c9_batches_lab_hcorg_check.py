"""batches: CHECK constraint on lab_h_corg range [0.1, 1.5]

Phase 15-D: the permanence ratio determines issuance, so its plausibility bound
belongs in the schema, not only in the LabHCorgRequest API model. Enforces
lab_h_corg IS NULL OR (lab_h_corg BETWEEN 0.1 AND 1.5).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK = "ck_batches_lab_h_corg_range"
_COND = "lab_h_corg IS NULL OR (lab_h_corg >= 0.1 AND lab_h_corg <= 1.5)"


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.create_check_constraint(_CK, _COND)


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_constraint(_CK, type_="check")
