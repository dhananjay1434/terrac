"""portal_users: add org_id + org_admin role (V8 Part 5 D — multi-tenancy)

Additive: a nullable org_id column (NULL = unscoped, sees everything — the
default and only state for every existing user, so this is fully backward
compatible) plus widening the role CHECK constraint to also allow
'org_admin'. No existing row's role or org_id changes.

Revision ID: b7c1d2e3f4a5
Revises: 58f424124234
Create Date: 2026-07-22 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, None] = '58f424124234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK = "ck_portal_users_role"
_OLD_COND = "role IN ('admin', 'lab', 'verifier')"
_NEW_COND = "role IN ('admin', 'lab', 'verifier', 'org_admin')"


def upgrade() -> None:
    with op.batch_alter_table("portal_users") as batch_op:
        batch_op.add_column(sa.Column("org_id", sa.String(length=128), nullable=True))
        batch_op.drop_constraint(_CK, type_="check")
        batch_op.create_check_constraint(_CK, _NEW_COND)


def downgrade() -> None:
    with op.batch_alter_table("portal_users") as batch_op:
        batch_op.drop_constraint(_CK, type_="check")
        batch_op.create_check_constraint(_CK, _OLD_COND)
        batch_op.drop_column("org_id")
