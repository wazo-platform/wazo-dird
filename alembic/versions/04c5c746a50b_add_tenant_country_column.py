"""add tenant country column

Revision ID: 04c5c746a50b
Revises: 60908d56d098

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '04c5c746a50b'
down_revision = '60908d56d098'


tenant_table_name = 'dird_tenant'


def upgrade():
    op.add_column(
        tenant_table_name,
        sa.Column(
            'country',
            sa.String(2),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column(tenant_table_name, 'country')
