"""remove slashes from phonebook names

Revision ID: 4bd4e843802a
Revises: 2adc8aff56ea

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '4bd4e843802a'
down_revision = '2adc8aff56ea'


source_table = sa.table(
    'dird_source',
    sa.column('uuid'),
    sa.column('name'),
)

display_table = sa.table(
    'dird_display',
    sa.column('uuid'),
    sa.column('name'),
)


def upgrade():
    source_query = sa.sql.select([source_table.c.uuid, source_table.c.name]).where(
        source_table.c.name.contains('/')
    )
    display_query = sa.sql.select([display_table.c.uuid, display_table.c.name]).where(
        display_table.c.name.contains('/')
    )
    for elem in op.get_bind().execute(source_query):
        op.execute(
            source_table.update()
            .where(source_table.c.uuid == elem.uuid)
            .values(name=elem.name.replace('/', '_'))
        )

    for elem in op.get_bind().execute(display_query):
        op.execute(
            display_table.update()
            .where(display_table.c.uuid == elem.uuid)
            .values(name=elem.name.replace('/', '_'))
        )


def downgrade():
    pass
