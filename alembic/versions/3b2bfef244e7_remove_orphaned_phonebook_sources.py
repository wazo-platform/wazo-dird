"""remove orphaned phonebook sources

Revision ID: 3b2bfef244e7
Revises: bb2cd24f0500
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '3b2bfef244e7'
down_revision = 'a3a7212e29b8'


source_table = sa.table(
    'dird_source',
    sa.column('uuid'),
    sa.column('extra_fields'),
    sa.column('tenant_uuid'),
    sa.column('backend'),
    sa.column('phonebook_uuid'),
)


def upgrade():
    query = source_table.delete().where(
        sa.and_(
            source_table.c.backend == 'phonebook',
            source_table.c.phonebook_uuid.is_(None),
        )
    )
    op.get_bind().execute(query)


def downgrade():
    pass
