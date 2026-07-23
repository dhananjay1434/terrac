"""create_credit_issuance (PR-1 — credit issuance ledger)

New table only — no existing table is touched, so this is fully additive
and backward compatible. A registry credit becomes a serialized,
issue-exactly-once unit (one issuance per batch, enforced by a unique
constraint on batch_uuid) instead of a bare number on the batch row.

Revision ID: c3b4875454a4
Revises: fbad0d51b1b1
Create Date: 2026-07-23 11:19:44.221854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3b4875454a4'
down_revision: Union[str, None] = 'fbad0d51b1b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "credit_issuances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("issuance_uuid", sa.String(length=36), nullable=False),
        sa.Column("batch_uuid", sa.String(length=36), nullable=False),
        sa.Column("serial", sa.String(length=128), nullable=True),
        sa.Column("vintage", sa.Integer(), nullable=True),
        sa.Column("t_co2e_frozen", sa.Float(), nullable=True),
        sa.Column("methodology_version", sa.String(length=255), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("verified_by_user_id", sa.Integer(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registry_submission_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_uuid"], ["batches.batch_uuid"]),
        sa.UniqueConstraint("issuance_uuid"),
        sa.UniqueConstraint("serial"),
        sa.UniqueConstraint("batch_uuid", name="uq_credit_issuances_batch_uuid"),
    )
    op.create_index(
        "ix_credit_issuances_issuance_uuid",
        "credit_issuances",
        ["issuance_uuid"],
    )
    op.create_index(
        "ix_credit_issuances_batch_uuid",
        "credit_issuances",
        ["batch_uuid"],
    )


def downgrade() -> None:
    op.drop_index("ix_credit_issuances_batch_uuid", table_name="credit_issuances")
    op.drop_index("ix_credit_issuances_issuance_uuid", table_name="credit_issuances")
    op.drop_table("credit_issuances")
