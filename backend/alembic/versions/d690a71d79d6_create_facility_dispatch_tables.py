"""create_facility_dispatch_tables

V8 Part 3.1 — Facility + Dispatch + DispatchSite: the custody-transfer
primitive (biomass/biochar moving between locations under different
custodians). Purely additive: three new tables only, no existing column
touched. `dispatches.dest_facility_uuid` is intentionally a plain column, NOT
a DB-enforced FK (mirrors Batch.project_id / SourceParcel — a device may
dispatch to a facility that hasn't synced to the portal's view yet).

Revision ID: d690a71d79d6
Revises: 840b80dc3102
Create Date: 2026-07-22 12:26:18.753018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd690a71d79d6'
down_revision: Union[str, None] = '840b80dc3102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "facilities",
        sa.Column("facility_uuid", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(128), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("facility_type", sa.String(16), nullable=False),
        sa.Column("state", sa.String(128), nullable=True),
        sa.Column("district", sa.String(128), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("registry_config_id", sa.String(128), nullable=True),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default=sa.text("'active'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "dispatches",
        sa.Column("dispatch_uuid", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source_ref", sa.String(128), nullable=True),
        sa.Column("dest_facility_uuid", sa.String(36), nullable=True),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default=sa.text("'draft'")
        ),
        sa.Column("weight_source_kg", sa.Float(), nullable=True),
        sa.Column("weight_source_method", sa.String(64), nullable=True),
        sa.Column("weight_facility_kg", sa.Float(), nullable=True),
        sa.Column("weight_delta_kg", sa.Float(), nullable=True),
        sa.Column("weight_delta_pct", sa.Float(), nullable=True),
        sa.Column("weight_flagged", sa.Boolean(), nullable=True),
        sa.Column("driver_name", sa.String(255), nullable=True),
        sa.Column("driver_phone", sa.String(32), nullable=True),
        sa.Column("truck_number", sa.String(32), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("sync_status", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_dispatches_dest_facility_uuid", "dispatches", ["dest_facility_uuid"]
    )
    op.create_index("ix_dispatches_device_id", "dispatches", ["device_id"])

    op.create_table(
        "dispatch_sites",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dispatch_uuid", sa.String(36), nullable=False),
        sa.Column("parcel_uuid", sa.String(36), nullable=True),
        sa.Column("moisture_pct", sa.Float(), nullable=True),
        sa.Column("truck_percentage_filled", sa.Float(), nullable=True),
    )
    op.create_index(
        "ix_dispatch_sites_dispatch_uuid", "dispatch_sites", ["dispatch_uuid"]
    )


def downgrade() -> None:
    op.drop_index("ix_dispatch_sites_dispatch_uuid", table_name="dispatch_sites")
    op.drop_table("dispatch_sites")
    op.drop_index("ix_dispatches_device_id", table_name="dispatches")
    op.drop_index("ix_dispatches_dest_facility_uuid", table_name="dispatches")
    op.drop_table("dispatches")
    op.drop_table("facilities")
