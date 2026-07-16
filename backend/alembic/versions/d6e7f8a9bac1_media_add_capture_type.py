"""media_files: add capture_type / capture_type_verified

Evidence-step label. `capture_type` is an OPTIONAL client hint (X-Capture-Type
header, unsigned); `capture_type_verified` flips True only when the server
corroborates the label against the Ed25519-signed telemetry smoke_evidence
pairs. Both additive: `capture_type` nullable, `capture_type_verified` non-null
defaulting False so legacy rows read as unverified.

Revision ID: d6e7f8a9bac1
Revises: c5d6e7f8a9ba
Create Date: 2026-07-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9bac1"
down_revision: Union[str, None] = "c5d6e7f8a9ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(
            sa.Column("capture_type", sa.String(64), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "capture_type_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_column("capture_type_verified")
        batch_op.drop_column("capture_type")
