"""remove the db_uri from the personal source

Revision ID: efe763372855
Revises: 86b01bf14e21

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'efe763372855'
down_revision = '86b01bf14e21'

source_table = sa.sql.table(
    'dird_source', sa.sql.column('extra_fields'), sa.sql.column('backend')
)


def upgrade():
    op.execute(
        source_table.update()
        .where(source_table.c.backend == 'personal')
        .values(extra_fields=None)
    )


def downgrade():
    extra_fields = (
        '''{"db_uri": "postgresql://asterisk:proformatique@localhost/asterisk"}'''
    )
    op.execute(
        source_table.update()
        .where(source_table.c.backend == 'personal')
        .values(extra_fields=extra_fields)
    )
