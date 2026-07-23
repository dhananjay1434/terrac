"""project_feedstock_and_client_target (FM-1)

Additive: two nullable columns on projects. NULL allowed_feedstocks = a
legacy project (registered before this Part) — grandfathered, no behavior
change (the app/backend fall back to the module-default positive list when
a project hasn't declared one). client_target is purely informational, not
enforced as a cap.

Revision ID: 653b964bf1c2
Revises: 25dde946cadb
Create Date: 2026-07-23 16:58:48.950268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '653b964bf1c2'
down_revision: Union[str, None] = '25dde946cadb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects", sa.Column("allowed_feedstocks", sa.Text(), nullable=True)
    )
    op.add_column(
        "projects", sa.Column("client_target", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("projects", "client_target")
    op.drop_column("projects", "allowed_feedstocks")
