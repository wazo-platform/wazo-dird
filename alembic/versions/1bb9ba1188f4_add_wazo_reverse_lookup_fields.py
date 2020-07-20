"""add wazo reverse lookup fields

Revision ID: 1bb9ba1188f4
Revises: c6062783c09c

"""

from alembic import op
from sqlalchemy import sql


# revision identifiers, used by Alembic.
revision = '1bb9ba1188f4'
down_revision = 'c6062783c09c'

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
        if 'exten' not in source.first_matched_columns:
            source.first_matched_columns.append('exten')
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
