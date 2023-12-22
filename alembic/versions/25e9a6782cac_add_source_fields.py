"""add source fields

Revision ID: 25e9a6782cac
Revises: 9a38ab587987

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, HSTORE, JSON

from alembic import op

# revision identifiers, used by Alembic.
revision = '25e9a6782cac'
down_revision = '9a38ab587987'


def upgrade():
    table_name = 'dird_source'

    op.add_column(
        table_name,
        sa.Column('tenant_uuid', sa.String(36), sa.ForeignKey('dird_tenant.uuid')),
    )
    op.add_column(table_name, sa.Column('searched_columns', ARRAY(sa.Text)))
    op.add_column(table_name, sa.Column('first_matched_columns', ARRAY(sa.Text)))
    op.add_column(table_name, sa.Column('format_columns', HSTORE))
    op.add_column(table_name, sa.Column('extra_fields', JSON))
    op.create_unique_constraint(
        'dird_source_tenant_name', table_name, ['tenant_uuid', 'name']
    )
    op.drop_constraint('dird_source_name_key', table_name)


def downgrade():
    pass
