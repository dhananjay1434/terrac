"""media_files: drop batch_uuid -> batches foreign key (T3.1)

The baseline migration created media_files with a ForeignKeyConstraint on
batch_uuid -> batches.batch_uuid. That FK forbids the app's deferred-anchoring
flow (a photo can legitimately be uploaded BEFORE its batch exists, then linked
by _evaluate_anchor). SQLite silently ignores foreign keys, so this went
unnoticed; on Postgres it raised ForeignKeyViolationError and broke 11 media
tests. The five sibling evidence tables never had such an FK. Drop it so media
matches its siblings and the field flow works on any FK-enforcing engine.

Postgres-only: SQLite can't ALTER DROP CONSTRAINT (and never enforced the FK
anyway), and this repo runs migrations exclusively against Postgres — the
SQLite test path builds schema via Base.metadata.create_all with the FK already
removed from the model. The FK name is discovered by inspection rather than
hardcoded, so it survives any auto-naming difference.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    insp = sa.inspect(bind)
    for fk in insp.get_foreign_keys("media_files"):
        if fk.get("referred_table") == "batches" and "batch_uuid" in fk.get(
            "constrained_columns", []
        ):
            op.drop_constraint(fk["name"], "media_files", type_="foreignkey")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.create_foreign_key(
        "media_files_batch_uuid_fkey",
        "media_files",
        "batches",
        ["batch_uuid"],
        ["batch_uuid"],
    )
