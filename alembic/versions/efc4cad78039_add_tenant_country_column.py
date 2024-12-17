"""add tenant country column

Revision ID: efc4cad78039
Revises: 7c49d771407a

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'efc4cad78039'
down_revision = '7c49d771407a'

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
