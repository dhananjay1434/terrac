"""portal: users + sessions (P2.1)

Additive tables for the Lab & Verifier portal: `portal_users` (email-unique,
argon2 password hash, role admin/lab/verifier, disabled flag) and
`portal_sessions` (sha256 of the opaque bearer token, user_id, expiry). No
existing table is touched.

Revision ID: a3b4c5d6e7f8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portal_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin', 'lab', 'verifier')",
            name="ck_portal_users_role",
        ),
        sa.UniqueConstraint("email", name="uq_portal_users_email"),
    )
    op.create_index("ix_portal_users_email", "portal_users", ["email"])

    op.create_table(
        "portal_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_portal_sessions_token_hash"),
    )
    op.create_index(
        "ix_portal_sessions_token_hash", "portal_sessions", ["token_hash"]
    )
    op.create_index("ix_portal_sessions_user_id", "portal_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_sessions_user_id", table_name="portal_sessions")
    op.drop_index("ix_portal_sessions_token_hash", table_name="portal_sessions")
    op.drop_table("portal_sessions")
    op.drop_index("ix_portal_users_email", table_name="portal_users")
    op.drop_table("portal_users")
