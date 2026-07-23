"""create_day_start_audits_table (PR-5.1a)

New table only — additive, no existing table touched. The prerequisite
server-side record for a day-start audit; R6 shipped the attestation
client-only (SharedPreferences), so there was no subject_uuid to attach
evidence media to until this row exists.

Revision ID: 01601107f242
Revises: c3b4875454a4
Create Date: 2026-07-23 12:32:34.212718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01601107f242'
down_revision: Union[str, None] = 'c3b4875454a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "day_start_audits",
        sa.Column("audit_uuid", sa.String(length=36), primary_key=True),
        sa.Column("facility_uuid", sa.String(length=36), nullable=False),
        sa.Column("audit_date", sa.String(length=10), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "facility_uuid", "audit_date", name="uq_day_start_audits_facility_date"
        ),
    )
    op.create_index(
        "ix_day_start_audits_facility_uuid", "day_start_audits", ["facility_uuid"]
    )
    op.create_index(
        "ix_day_start_audits_device_id", "day_start_audits", ["device_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_day_start_audits_device_id", table_name="day_start_audits")
    op.drop_index("ix_day_start_audits_facility_uuid", table_name="day_start_audits")
    op.drop_table("day_start_audits")
