"""add conference reverse lookup fields

Revision ID: c6062783c09c
Revises: 0542e068b5ef

"""

from alembic import op
from sqlalchemy import sql


# revision identifiers, used by Alembic.
revision = 'c6062783c09c'
down_revision = '0542e068b5ef'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('first_matched_columns'),
    sql.column('format_columns'),
    sql.column('backend'),
)


def upgrade():
    for source in get_conference_sources():
        if 'extensions' not in source.first_matched_columns:
            source.first_matched_columns.append('extensions')
        if 'incalls' not in source.first_matched_columns:
            source.first_matched_columns.append('incalls')
        source.format_columns.setdefault('reverse', '{name}')

        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(
                first_matched_columns=source.first_matched_columns,
                format_columns=source.format_columns,
            )
        )
        op.get_bind().execute(query)


def get_conference_sources():
    conference_sources_query = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.format_columns,
            dird_source_table.c.first_matched_columns,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend == 'conference')

    return op.get_bind().execute(conference_sources_query)


def downgrade():
    pass
