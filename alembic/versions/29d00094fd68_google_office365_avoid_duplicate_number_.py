"""google/office365: avoid duplicate number in default columns

Revision ID: 29d00094fd68
Revises: 1bb9ba1188f4

"""

from alembic import op
from sqlalchemy import sql


# revision identifiers, used by Alembic.
revision = '29d00094fd68'
down_revision = '1bb9ba1188f4'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('format_columns'),
    sql.column('backend'),
)


def upgrade():
    dird_sources = get_google_sources()
    for source in dird_sources:
        update_google_source(source)

    dird_sources = get_office365_sources()
    for source in dird_sources:
        update_office365_source(source)


def get_google_sources():
    google_sources = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.format_columns,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend == 'google')
    return op.get_bind().execute(google_sources)


def update_google_source(source):
    if source.format_columns.get('phone') == '{numbers[0]}':
        source.format_columns['phone'] = '{numbers_except_label[mobile][0]}'
    query = (
        dird_source_table.update()
        .where(dird_source_table.c.uuid == source.uuid)
        .values(
            format_columns=source.format_columns,
        )
    )
    op.get_bind().execute(query)


def get_office365_sources():
    office365_sources = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.format_columns,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend == 'office365')
    return op.get_bind().execute(office365_sources)


def update_office365_source(source):
    if source.format_columns.get('phone') == '{numbers[0]}':
        source.format_columns['phone'] = '{numbers_except_label[mobilePhone][0]}'
    query = (
        dird_source_table.update()
        .where(dird_source_table.c.uuid == source.uuid)
        .values(
            format_columns=source.format_columns,
        )
    )
    op.get_bind().execute(query)


def downgrade():
    pass
