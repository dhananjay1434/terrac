"""create_registry_config_table

V8 Part 4 (G) — config-driven methodology/registry. Creates `registry_configs`
and seeds exactly ONE row, config_id='default', whose params_json matches the
hardcoded CSI-3.2 constants in lca_engine.py byte-for-byte (verified by
tests/test_registry_config.py, which asserts this seed equals
lca_engine.LcaParams() field-for-field — any future drift between this seed
and the module defaults fails that test immediately). Purely additive.

Revision ID: 8f0bb7661626
Revises: ad207421131d
Create Date: 2026-07-22 16:05:31.258864

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f0bb7661626'
down_revision: Union[str, None] = 'ad207421131d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirrors lca_engine.py's module-level CSI-3.2 constants exactly.
_DEFAULT_PARAMS = {
    "corg_table": {
        "Lantana_camara": 0.60,
        "Wood_chips": 0.55,
        "Agricultural_waste": 0.50,
        "Default": 0.55,
    },
    "safety_deduction_kg_per_t": 20.0,
    "transport_factor_kg_per_t_km": 0.01194,
    "transport_threshold_km": 100.0,
    "ch4_compliant_kg_per_t": 0.005,
    "ch4_non_compliant_kg_per_t": 30.0,
}


def upgrade() -> None:
    op.create_table(
        "registry_configs",
        sa.Column("config_id", sa.String(128), primary_key=True),
        sa.Column("registry_name", sa.String(255), nullable=False),
        sa.Column("methodology_version", sa.String(64), nullable=False),
        sa.Column(
            "params_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("fpic_template_set_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO registry_configs
                (config_id, registry_name, methodology_version, params_json)
            VALUES (:config_id, :registry_name, :methodology_version, :params_json)
            """
        ),
        {
            "config_id": "default",
            "registry_name": "Carbon Standards International",
            "methodology_version": "CSI-3.2",
            "params_json": json.dumps(_DEFAULT_PARAMS),
        },
    )


def downgrade() -> None:
    op.drop_table("registry_configs")
