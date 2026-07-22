"""create_app_config_table

V8 Part 0.4 — the `app_config` table backing the remote control plane
(signed feature flags / kill-switch / min-version, see routers/config.py).
Purely additive: a new table only, no existing column touched. An empty
table is the safe default state (see models.AppConfig docstring) — no
backfill needed.

Revision ID: 9f812d10294c
Revises: 1a901336bb62
Create Date: 2026-07-22 02:10:08.611242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f812d10294c'
down_revision: Union[str, None] = '1a901336bb62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column(
            "config_id",
            sa.String(32),
            primary_key=True,
            server_default=sa.text("'default'"),
        ),
        sa.Column(
            "flags_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("min_version", sa.String(32), nullable=True),
        sa.Column(
            "kill_switch",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_config")
