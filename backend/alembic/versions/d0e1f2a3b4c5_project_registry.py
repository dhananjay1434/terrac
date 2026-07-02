"""create C8 project-registry tables

Rainbow compliance C8: project-setup registry (admin-authenticated) — kilns,
operator training records, supervisor site-visit reports, scale calibrations.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kilns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kiln_id", sa.String(length=128), nullable=False),
        sa.Column("material", sa.String(length=128), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("lifetime_years", sa.Float(), nullable=True),
        sa.Column("kiln_type", sa.String(length=16), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kilns_kiln_id", "kilns", ["kiln_id"], unique=True)

    op.create_table(
        "operator_training",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("record_uuid", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.String(length=128), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_operator_training_record_uuid",
        "operator_training",
        ["record_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_operator_training_operator_id", "operator_training", ["operator_id"]
    )

    op.create_table(
        "supervisor_visits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("visit_uuid", sa.String(length=64), nullable=False),
        sa.Column("kiln_id", sa.String(length=128), nullable=True),
        sa.Column("report_sha256", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_supervisor_visits_visit_uuid",
        "supervisor_visits",
        ["visit_uuid"],
        unique=True,
    )
    op.create_index("ix_supervisor_visits_kiln_id", "supervisor_visits", ["kiln_id"])

    op.create_table(
        "scale_calibrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("calibration_uuid", sa.String(length=64), nullable=False),
        sa.Column("scale_id", sa.String(length=128), nullable=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_sha256", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scale_calibrations_calibration_uuid",
        "scale_calibrations",
        ["calibration_uuid"],
        unique=True,
    )
    op.create_index(
        "ix_scale_calibrations_scale_id", "scale_calibrations", ["scale_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_scale_calibrations_scale_id", table_name="scale_calibrations")
    op.drop_index(
        "ix_scale_calibrations_calibration_uuid", table_name="scale_calibrations"
    )
    op.drop_table("scale_calibrations")

    op.drop_index("ix_supervisor_visits_kiln_id", table_name="supervisor_visits")
    op.drop_index("ix_supervisor_visits_visit_uuid", table_name="supervisor_visits")
    op.drop_table("supervisor_visits")

    op.drop_index("ix_operator_training_operator_id", table_name="operator_training")
    op.drop_index("ix_operator_training_record_uuid", table_name="operator_training")
    op.drop_table("operator_training")

    op.drop_index("ix_kilns_kiln_id", table_name="kilns")
    op.drop_table("kilns")
