"""create field_walk_tracks table (V8 Part 5 A phase-2)

Purely additive: one new table, no existing column touched. Ground-truthed
boundary evidence from device GPS walks, authorized by a server-signed
field-walk link (reuses the Part 0.1 Ed25519 signing key).

Revision ID: c8d9e0f1a2b3
Revises: b7c1d2e3f4a5
Create Date: 2026-07-22 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_walk_tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "parcel_uuid",
            sa.String(length=36),
            sa.ForeignKey("source_parcels.parcel_uuid"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("link_nonce", sa.String(length=64), nullable=False),
        sa.Column("points_json", sa.Text(), nullable=False),
        sa.Column("computed_boundary_geojson", sa.Text(), nullable=False),
        sa.Column("computed_area_m2", sa.Float(), nullable=False),
        sa.Column("overlap_ratio_vs_declared", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("link_nonce", name="uq_field_walk_tracks_link_nonce"),
    )
    op.create_index(
        "ix_field_walk_tracks_parcel_uuid", "field_walk_tracks", ["parcel_uuid"]
    )
    op.create_index(
        "ix_field_walk_tracks_device_id", "field_walk_tracks", ["device_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_field_walk_tracks_device_id", table_name="field_walk_tracks")
    op.drop_index("ix_field_walk_tracks_parcel_uuid", table_name="field_walk_tracks")
    op.drop_table("field_walk_tracks")
