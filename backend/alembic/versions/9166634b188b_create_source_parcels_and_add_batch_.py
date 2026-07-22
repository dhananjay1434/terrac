"""create_source_parcels_and_add_batch_parcel_uuid

V8 Part 1.2 — introduces `source_parcels` table and adds `parcel_uuid` column to `batches`.
Fully additive and backward compatible. `batches.parcel_uuid` is nullable so existing batches grandfather cleanly.

Revision ID: 9166634b188b
Revises: 9f812d10294c
Create Date: 2026-07-22 02:27:38.564765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9166634b188b'
down_revision: Union[str, None] = '9f812d10294c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_parcels",
        sa.Column("parcel_uuid", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(128), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("boundary_geojson", sa.Text(), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=False),
        sa.Column("declared_area_acres", sa.Float(), nullable=True),
        sa.Column("bbox_min_lat", sa.Float(), nullable=False),
        sa.Column("bbox_min_lon", sa.Float(), nullable=False),
        sa.Column("bbox_max_lat", sa.Float(), nullable=False),
        sa.Column("bbox_max_lon", sa.Float(), nullable=False),
        sa.Column("boundary_method", sa.String(64), nullable=False, server_default=sa.text("'portal_drawn'")),
        sa.Column("boundary_status", sa.String(64), nullable=False, server_default=sa.text("'approved'")),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("portal_users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_source_parcels_project_id", "source_parcels", ["project_id"])
    op.create_index("ix_source_parcels_bbox_min_lat", "source_parcels", ["bbox_min_lat"])
    op.create_index("ix_source_parcels_bbox_min_lon", "source_parcels", ["bbox_min_lon"])
    op.create_index("ix_source_parcels_bbox_max_lat", "source_parcels", ["bbox_max_lat"])
    op.create_index("ix_source_parcels_bbox_max_lon", "source_parcels", ["bbox_max_lon"])

    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("parcel_uuid", sa.String(36), nullable=True))
        batch_op.create_index("ix_batches_parcel_uuid", ["parcel_uuid"])


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_index("ix_batches_parcel_uuid")
        batch_op.drop_column("parcel_uuid")

    op.drop_index("ix_source_parcels_bbox_max_lon", table_name="source_parcels")
    op.drop_index("ix_source_parcels_bbox_max_lat", table_name="source_parcels")
    op.drop_index("ix_source_parcels_bbox_min_lon", table_name="source_parcels")
    op.drop_index("ix_source_parcels_bbox_min_lat", table_name="source_parcels")
    op.drop_index("ix_source_parcels_project_id", table_name="source_parcels")
    op.drop_table("source_parcels")
