"""update office365 default number columns

Revision ID: 3966fb49ce71
Revises: e91a7fea4af6

"""

from alembic import op
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '3966fb49ce71'
down_revision = 'e91a7fea4af6'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('searched_columns'),
    sql.column('first_matched_columns'),
    sql.column('format_columns'),
    sql.column('backend'),
)


def upgrade():
    dird_sources = get_office365_sources()
    for source in dird_sources:
        if 'homePhones' not in source.searched_columns:
            source.searched_columns.append('homePhones')
        if 'mobilePhone' not in source.searched_columns:
            source.searched_columns.append('mobilePhone')
        if 'homePhones' not in source.first_matched_columns:
            source.first_matched_columns.append('homePhones')
        source.format_columns['phone_mobile'] = '{mobilePhone}'
        source.format_columns['number'] = '{numbers[0]}'
        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(
                searched_columns=source.searched_columns,
                first_matched_columns=source.first_matched_columns,
                format_columns=source.format_columns,
            )
        )
        op.get_bind().execute(query)


def get_office365_sources():
    office365_sources = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.searched_columns,
            dird_source_table.c.first_matched_columns,
            dird_source_table.c.format_columns,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend == 'office365')
    return op.get_bind().execute(office365_sources)


def downgrade():
    pass
