"""media_files: add exif_lat / exif_lon

Phase 9: the server parses GPS from the uploaded photo's EXIF and stores it so a
batch's claimed coordinates can be corroborated against the photo. Both columns
are nullable (an upload may carry no EXIF GPS).

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.add_column(sa.Column("exif_lat", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("exif_lon", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("media_files") as batch_op:
        batch_op.drop_column("exif_lon")
        batch_op.drop_column("exif_lat")
