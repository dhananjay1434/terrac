"""device_keys hmac_key to public_key

Phase 5: device identity migrates from a symmetric HMAC key to an Ed25519
public key. The column is renamed (data is preserved as-is; operators must
re-enroll devices so the stored value is actually a public key).

Revision ID: d7e8f9a0b1c2
Revises: 8fd65cb412f6
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "8fd65cb412f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("device_keys") as batch_op:
        batch_op.alter_column("hmac_key", new_column_name="public_key")


def downgrade() -> None:
    with op.batch_alter_table("device_keys") as batch_op:
        batch_op.alter_column("public_key", new_column_name="hmac_key")
