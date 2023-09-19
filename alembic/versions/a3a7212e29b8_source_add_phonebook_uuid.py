"""source-add-phonebook-uuid

Revision ID: a3a7212e29b8
Revises: 3b2bfef244e7

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a3a7212e29b8'
down_revision = '3b2bfef244e7'

source_table = sa.table(
    'dird_source',
    sa.column('uuid'),
    sa.column('extra_fields'),
    sa.column('backend'),
    sa.column('phonebook_uuid'),
)


def upgrade():
    op.add_column(
        'dird_source',
        sa.Column(
            'phonebook_uuid',
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey('dird_phonebook.uuid', ondelete='CASCADE'),
            nullable=True,
        ),
    )
    query = sa.select(
        [
            source_table.c.uuid,
            source_table.c.extra_fields,
        ]
    ).where(source_table.c.backend == 'phonebook')

    phonebook_uuid_map = {}
    for row in op.get_bind().execute(query):
        phonebook_uuid_map[row.uuid] = row.extra_fields['phonebook_uuid']

    for source_uuid, phonebook_uuid in phonebook_uuid_map.items():
        query = (
            source_table.update()
            .where(
                source_table.c.uuid == source_uuid,
            )
            .values(phonebook_uuid=phonebook_uuid)
        )
        op.get_bind().execute(query)


def downgrade():
    op.drop_column('dird_source', 'phonebook_uuid')
