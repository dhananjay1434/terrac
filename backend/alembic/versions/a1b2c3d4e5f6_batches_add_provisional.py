"""batches: add provisional flag

Phase 8: a carbon credit computed without a lab-measured H:Corg is PROVISIONAL
(it falls back to the conservative 0.35 assumption) and must never be issued as
final. This is tracked on a dedicated boolean column rather than overloading
`status`, which encodes photo-evidence anchoring (RECEIVED/UNVERIFIED) — the two
concerns are orthogonal. Existing rows backfill to TRUE (treat legacy,
assumption-based credits as provisional until reviewed).

Revision ID: a1b2c3d4e5f6
Revises: d7e8f9a0b1c2
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(
            sa.Column(
                "provisional",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_column("provisional")
