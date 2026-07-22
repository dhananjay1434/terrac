"""add_media_verification_status

V8 Part 4 (K) — per-media reviewer verdict loop. Adds two nullable columns to
media_files: verification_status ('approved'|'rejected'|NULL=unreviewed) and
verification_remarks (free text). Purely additive.

Revision ID: ad207421131d
Revises: d690a71d79d6
Create Date: 2026-07-22 15:44:47.675103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad207421131d'
down_revision: Union[str, None] = 'd690a71d79d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(
            sa.Column("verification_status", sa.String(16), nullable=True)
        )
        batch_op.add_column(
            sa.Column("verification_remarks", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_column("verification_remarks")
        batch_op.drop_column("verification_status")
