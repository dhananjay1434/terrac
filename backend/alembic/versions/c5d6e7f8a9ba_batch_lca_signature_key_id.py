"""batches: lca_signature_key_id for versioned HMAC keys (P3.6)

Additive nullable column recording which versioned HMAC key produced a batch's
lca_signature. Null on historical rows ⇒ resolves to the legacy key id k0, so
rotating the active key never invalidates already-issued signatures.

Revision ID: c5d6e7f8a9ba
Revises: b4c5d6e7f8a9
Create Date: 2026-07-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9ba"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batches",
        sa.Column("lca_signature_key_id", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("batches", "lca_signature_key_id")
