"""remove the db_uri from the phonebook source

Revision ID: 07e71f4c5437
Revises: efe763372855

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '07e71f4c5437'
down_revision = 'efe763372855'

source_table = sa.sql.table(
    'dird_source', sa.sql.column('extra_fields'), sa.sql.column('backend')
)


def upgrade():
    op.execute(
        source_table.update()
        .where(source_table.c.backend == 'phonebook')
        .values(extra_fields=None)
    )


def downgrade():
    extra_fields = (
        '''{"db_uri": "postgresql://asterisk:proformatique@localhost/asterisk"}'''
    )
    op.execute(
        source_table.update()
        .where(source_table.c.backend == 'phonebook')
        .values(extra_fields=extra_fields)
    )
