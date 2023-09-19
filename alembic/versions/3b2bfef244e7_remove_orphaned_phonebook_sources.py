"""remove-orphaned-phonebook-sources

Revision ID: 3b2bfef244e7
Revises: bb2cd24f0500

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b2bfef244e7'
down_revision = 'bb2cd24f0500'

phonebook_table = sa.table(
    'dird_phonebook',
    sa.column('uuid'),
    sa.column('tenant_uuid'),
)

source_table = sa.table(
    'dird_source',
    sa.column('uuid'),
    sa.column('extra_fields'),
    sa.column('tenant_uuid'),
    sa.column('backend'),
)


def upgrade():
    phonebooks = {}
    sources = {}

    query = sa.select(
        [
            phonebook_table.c.uuid,
            phonebook_table.c.tenant_uuid,
        ]
    )
    for row in op.get_bind().execute(query):
        phonebooks[str(row.uuid)] = str(row.tenant_uuid)

    query = sa.select(
        [
            source_table.c.uuid,
            source_table.c.extra_fields,
            source_table.c.tenant_uuid,
        ]
    ).where(source_table.c.backend == 'phonebook')
    for row in op.get_bind().execute(query):
        phonebook_uuid = str(row.extra_fields.get('phonebook_uuid'))
        sources[row.uuid] = {
            'tenant_uuid': str(row.tenant_uuid),
            'phonebook_uuid': phonebook_uuid,
        }

    to_delete = set()
    for source_uuid, source_details in sources.items():
        phonebook_uuid = source_details['phonebook_uuid']
        if not phonebook_uuid:
            to_delete.add(source_uuid)
        elif phonebook_uuid not in phonebooks:
            to_delete.add(source_uuid)
        elif source_details['tenant_uuid'] != phonebooks[phonebook_uuid]:
            to_delete.add(source_uuid)

    query = source_table.delete().where(source_table.c.uuid.in_(to_delete))
    op.get_bind().execute(query)


def downgrade():
    pass
