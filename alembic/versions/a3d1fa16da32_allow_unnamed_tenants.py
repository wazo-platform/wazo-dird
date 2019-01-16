"""allow unnamed tenants

Revision ID: a3d1fa16da32
Revises: 401aca548ddf

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'a3d1fa16da32'
down_revision = '401aca548ddf'


def upgrade():
    table_name = 'dird_tenant'
    op.alter_column(table_name, 'name', nullable=True)
    op.drop_constraint('dird_tenant_name_check', table_name)


def downgrade():
    pass
