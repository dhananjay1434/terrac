"""hierarchy_v2: networks table + additive site/kiln/batch hierarchy columns (M1.1)

All additive (new table + nullable columns), so every existing row and the
Tier-0 flow are unaffected. batch_code is UNIQUE (audit A3: permanent codes,
NULL until lineage known). kilns.sensor_profile is a DECLARED display hint
(default 'none'); the real tier is always derived from what streams
(Global Rule 10).

Revision ID: a7f3c1b9d2e4
Revises: 653b964bf1c2
Create Date: 2026-07-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7f3c1b9d2e4"
down_revision: Union[str, None] = "653b964bf1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROFILES = "sensor_profile IN ('none', 'load_only', 'thermal_only', 'full')"


def upgrade() -> None:
    op.create_table(
        "networks",
        sa.Column("network_id", sa.String(length=64), primary_key=True),
        sa.Column("org_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country_code", sa.String(length=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_networks_org_id", "networks", ["org_id"])

    with op.batch_alter_table("facilities") as batch_op:
        batch_op.add_column(sa.Column("network_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("site_code", sa.String(length=16), nullable=True))
    op.create_index("ix_facilities_network_id", "facilities", ["network_id"])

    with op.batch_alter_table("kilns") as batch_op:
        batch_op.add_column(sa.Column("site_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("kiln_code", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column(
                "sensor_profile",
                sa.String(length=16),
                nullable=False,
                server_default="none",
            )
        )
        batch_op.create_check_constraint("ck_kilns_sensor_profile", _PROFILES)
    op.create_index("ix_kilns_site_id", "kilns", ["site_id"])

    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("batch_code", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("network_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("site_id", sa.String(length=64), nullable=True))
    op.create_index("ix_batches_batch_code", "batches", ["batch_code"], unique=True)
    op.create_index("ix_batches_network_id", "batches", ["network_id"])
    op.create_index("ix_batches_site_id", "batches", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_batches_site_id", table_name="batches")
    op.drop_index("ix_batches_network_id", table_name="batches")
    op.drop_index("ix_batches_batch_code", table_name="batches")
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_column("site_id")
        batch_op.drop_column("network_id")
        batch_op.drop_column("batch_code")

    op.drop_index("ix_kilns_site_id", table_name="kilns")
    with op.batch_alter_table("kilns") as batch_op:
        batch_op.drop_constraint("ck_kilns_sensor_profile", type_="check")
        batch_op.drop_column("sensor_profile")
        batch_op.drop_column("kiln_code")
        batch_op.drop_column("site_id")

    op.drop_index("ix_facilities_network_id", table_name="facilities")
    with op.batch_alter_table("facilities") as batch_op:
        batch_op.drop_column("site_code")
        batch_op.drop_column("network_id")

    op.drop_index("ix_networks_org_id", table_name="networks")
    op.drop_table("networks")
