"""create_project_table_and_backfill

V8 Part 0.2 — introduces the `projects` table (Batch.project_id and
AnnualVerification.project_id were bare strings with no backing entity).
Purely additive: creates a new table, then backfills one row per distinct
existing project_id value found in `batches` / `annual_verifications` so no
existing row references an unknown project. No existing column is altered,
dropped, or constrained — old app/backend versions are unaffected.

The backfill INSERT..SELECT..WHERE NOT IN is idempotent (safe to re-run) and
engine-agnostic (tested against both the SQLite test suite and Postgres).

Revision ID: 1a901336bb62
Revises: d6e7f8a9bac1
Create Date: 2026-07-22 01:50:08.489480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a901336bb62'
down_revision: Union[str, None] = 'd6e7f8a9bac1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("registry_config_id", sa.String(128), nullable=True),
        sa.Column("org_id", sa.String(128), nullable=True),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default=sa.text("'active'")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Backfill: one project row per distinct project_id already referenced by
    # existing data, so no batch/annual-verification is left pointing at an
    # unregistered project. `name` defaults to the project_id itself (an
    # admin can rename later via the portal) — never fabricated metadata,
    # just an honest placeholder using data we already have.
    for source_table in ("batches", "annual_verifications"):
        op.execute(
            sa.text(
                f"""
                INSERT INTO projects (project_id, name, status, created_at)
                SELECT DISTINCT project_id, project_id, 'active', CURRENT_TIMESTAMP
                FROM {source_table}
                WHERE project_id IS NOT NULL
                  AND project_id NOT IN (SELECT project_id FROM projects)
                """
            )
        )


def downgrade() -> None:
    op.drop_table("projects")
