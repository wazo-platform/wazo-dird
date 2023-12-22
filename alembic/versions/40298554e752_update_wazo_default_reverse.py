"""update_wazo_default_reverse

Revision ID: 40298554e752
Revises: 69698e576ad7

"""

from sqlalchemy import sql

from alembic import op

# revision identifiers, used by Alembic.
revision = '40298554e752'
down_revision = '69698e576ad7'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('first_matched_columns'),
    sql.column('format_columns'),
    sql.column('backend'),
)


def upgrade():
    dird_sources = get_wazo_sources()
    for source in dird_sources:
        if 'mobile_phone_number' not in source.first_matched_columns:
            source.first_matched_columns.append('mobile_phone_number')
        source.format_columns['reverse'] = '{firstname} {lastname}'
        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(
                first_matched_columns=source.first_matched_columns,
                format_columns=source.format_columns,
            )
        )
        op.get_bind().execute(query)


def get_wazo_sources():
    wazo_sources = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.first_matched_columns,
            dird_source_table.c.format_columns,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend == 'wazo')
    return op.get_bind().execute(wazo_sources)


def downgrade():
    pass
