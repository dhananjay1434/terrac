"""create composite_pile_samples table

Rainbow compliance C4: one site composite pile sub-sample per row (many per
batch). batch_uuid is indexed but NOT unique; sample_uuid is unique.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "composite_pile_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sample_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_composite_pile_samples_sample_uuid",
        "composite_pile_samples",
        ["sample_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_composite_pile_samples_batch_uuid",
        "composite_pile_samples",
        ["batch_uuid"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_composite_pile_samples_batch_uuid",
        table_name="composite_pile_samples",
    )
    op.drop_index(
        "ix_composite_pile_samples_sample_uuid",
        table_name="composite_pile_samples",
    )
    op.drop_table("composite_pile_samples")
