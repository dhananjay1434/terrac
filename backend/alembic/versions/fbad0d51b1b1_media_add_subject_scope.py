"""media_add_subject_scope

V8 deferred R1 — entity-scoped media (farmer + dispatch). Additive: two nullable
columns + an index on media_files. Legacy media rows keep NULL subject_type and
remain batch-scoped via the existing batch_uuid column. No data rewrite.

Revision ID: fbad0d51b1b1
Revises: c8d9e0f1a2b3
Create Date: 2026-07-22 21:20:45.639466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbad0d51b1b1'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(sa.Column("subject_type", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("subject_uuid", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_media_files_subject_uuid", ["subject_uuid"])


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_index("ix_media_files_subject_uuid")
        batch_op.drop_column("subject_uuid")
        batch_op.drop_column("subject_type")
