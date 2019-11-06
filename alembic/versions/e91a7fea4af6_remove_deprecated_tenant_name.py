"""remove-deprecated-tenant-name

Revision ID: e91a7fea4af6
Revises: 17914dbfe398

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e91a7fea4af6'
down_revision = '17914dbfe398'

table_name = 'dird_tenant'
column_name = 'name'


def upgrade():
    op.drop_column(table_name, column_name)


def downgrade():
    op.add_column(table_name, sa.Column(column_name, sa.String(255)))
