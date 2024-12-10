"""migrate phonebook source names

Revision ID: 60908d56d098
Revises: 042a2ba167c0

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '60908d56d098'
down_revision = '042a2ba167c0'

dird_source_table = sa.sql.table(
    'dird_source',
    sa.sql.column('uuid'),
    sa.sql.column('first_matched_columns'),
    sa.sql.column('format_columns'),
    sa.sql.column('backend'),
    sa.sql.column('name'),
)
phonebook_table = sa.table(
    'dird_phonebook',
    sa.column('uuid'),
    sa.column('name'),
    sa.column('id'),
    sa.column('tenant_uuid'),
)


def upgrade():
    op.alter_column(
        'dird_source',
        'name',
        server_default=sa.text('uuid_generate_v4()'),
    )
    op.execute(
        sa.sql.update(dird_source_table)
        .where(dird_source_table.c.backend == 'phonebook')
        .values(name=sa.text('uuid_generate_v4()'))
    )


def downgrade():
    pass
