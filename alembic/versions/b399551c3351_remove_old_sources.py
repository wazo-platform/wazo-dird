"""remove old sources

Revision ID: b399551c3351
Revises: 0f0470be22d4

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b399551c3351'
down_revision = '0f0470be22d4'


def upgrade():
    table_name = 'dird_source'
    source_table = sa.sql.table(table_name)
    query = source_table.delete()
    op.get_bind().execute(query)


def downgrade():
    pass
