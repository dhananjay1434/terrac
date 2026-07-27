"""m4_1_journeys_v2

Revision ID: cd12e28b1b89
Revises: 34be10860363
Create Date: 2026-07-27 13:31:41.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cd12e28b1b89'
down_revision = '74b54f6dc74e'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # new table dispatch_journeys
    op.create_table(
        'dispatch_journeys',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('dispatch_uuid', sa.String(length=36), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('vehicle_reg', sa.String(length=32), nullable=True),
        sa.Column('fuel_type', sa.String(length=16), nullable=True),
        sa.Column('emissions_kg', sa.Float(), nullable=True),
        sa.Column('factor_version', sa.String(length=16), nullable=True),
        sa.Column('route_geojson', sa.Text(), nullable=True)
    )
    op.create_index('ix_dispatch_journeys_dispatch_uuid', 'dispatch_journeys', ['dispatch_uuid'], unique=True)

    # new table dispatch_manifest_lines
    op.create_table(
        'dispatch_manifest_lines',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('dispatch_uuid', sa.String(length=36), nullable=False),
        sa.Column('container', sa.String(length=32), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.Column('unit_kg', sa.Float(), nullable=True),
        sa.Column('volume_l', sa.Float(), nullable=True),
        sa.Column('product', sa.String(length=64), nullable=True)
    )
    op.create_index('ix_dispatch_manifest_lines_dispatch_uuid', 'dispatch_manifest_lines', ['dispatch_uuid'], unique=False)

    # facilities and dispatch_sites add contact_name/contact_phone
    op.add_column('facilities', sa.Column('contact_name', sa.String(length=128), nullable=True))
    op.add_column('facilities', sa.Column('contact_phone', sa.String(length=32), nullable=True))

    op.add_column('dispatch_sites', sa.Column('contact_name', sa.String(length=128), nullable=True))
    op.add_column('dispatch_sites', sa.Column('contact_phone', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('dispatch_sites', 'contact_phone')
    op.drop_column('dispatch_sites', 'contact_name')
    
    op.drop_column('facilities', 'contact_phone')
    op.drop_column('facilities', 'contact_name')

    op.drop_index('ix_dispatch_manifest_lines_dispatch_uuid', table_name='dispatch_manifest_lines')
    op.drop_table('dispatch_manifest_lines')
    
    op.drop_index('ix_dispatch_journeys_dispatch_uuid', table_name='dispatch_journeys')
    op.drop_table('dispatch_journeys')
