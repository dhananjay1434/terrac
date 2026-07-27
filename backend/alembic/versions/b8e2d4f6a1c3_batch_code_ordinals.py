"""batch_code_ordinals: explicit ordinals for batch-code identity (ADR-001 B2)

Adds nullable ordinal/code columns + per-parent unique constraints so
make_batch_code has real numeric components (assigned, never derived). All
nullable — a NULL anywhere leaves batch_code NULL (audit A3 preserved).
networks.country_code already exists (hierarchy_v2), so it is NOT re-added.

Revision ID: b8e2d4f6a1c3
Revises: a7f3c1b9d2e4
Create Date: 2026-07-27 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e2d4f6a1c3"
down_revision: Union[str, None] = "a7f3c1b9d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("networks") as batch_op:
        batch_op.add_column(sa.Column("org_ordinal", sa.SmallInteger(), nullable=True))
        batch_op.add_column(sa.Column("network_code", sa.String(length=4), nullable=True))
        batch_op.create_unique_constraint(
            "uq_networks_org_ordinal", ["org_id", "org_ordinal"]
        )
        batch_op.create_unique_constraint(
            "uq_networks_network_code", ["org_id", "network_code"]
        )
    with op.batch_alter_table("facilities") as batch_op:
        batch_op.add_column(sa.Column("site_ordinal", sa.SmallInteger(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_facilities_site_ordinal", ["network_id", "site_ordinal"]
        )
    with op.batch_alter_table("kilns") as batch_op:
        batch_op.add_column(sa.Column("kiln_ordinal", sa.SmallInteger(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_kilns_kiln_ordinal", ["site_id", "kiln_ordinal"]
        )


def downgrade() -> None:
    with op.batch_alter_table("kilns") as batch_op:
        batch_op.drop_constraint("uq_kilns_kiln_ordinal", type_="unique")
        batch_op.drop_column("kiln_ordinal")
    with op.batch_alter_table("facilities") as batch_op:
        batch_op.drop_constraint("uq_facilities_site_ordinal", type_="unique")
        batch_op.drop_column("site_ordinal")
    with op.batch_alter_table("networks") as batch_op:
        batch_op.drop_constraint("uq_networks_network_code", type_="unique")
        batch_op.drop_constraint("uq_networks_org_ordinal", type_="unique")
        batch_op.drop_column("network_code")
        batch_op.drop_column("org_ordinal")
