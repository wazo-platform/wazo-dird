"""source-add-phonebook-uuid

Revision ID: a3a7212e29b8
Revises: 3b2bfef244e7

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a3a7212e29b8'
down_revision = 'bb2cd24f0500'

source_table = sa.table(
    'dird_source',
    sa.column('uuid'),
    sa.column('name'),
    sa.column('extra_fields'),
    sa.column('backend'),
    sa.column('phonebook_uuid'),
    sa.column('tenant_uuid'),
)
phonebook_table = sa.table(
    'dird_phonebook',
    sa.column('uuid'),
    sa.column('name'),
    sa.column('id'),
    sa.column('tenant_uuid'),
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
    op.create_unique_constraint(
        'dird_phonebook_tenant_uuid_idx',
        'dird_phonebook',
        ['uuid', 'tenant_uuid'],
    )
    op.create_foreign_key(
        'dird_source_phonebook_fkey',
        'dird_source',
        'dird_phonebook',
        ['phonebook_uuid', 'tenant_uuid'],
        ['uuid', 'tenant_uuid'],
        ondelete='CASCADE',
    )
    phonebook_sources_query = sa.select(
        [
            source_table.c.uuid,
            source_table.c.name,
            source_table.c.extra_fields,
            source_table.c.tenant_uuid,
        ]
    ).where(source_table.c.backend == 'phonebook')
    phonebooks_query = sa.select(
        [
            phonebook_table.c.uuid,
            phonebook_table.c.name,
            phonebook_table.c.id,
            phonebook_table.c.tenant_uuid,
        ]
    )
    phonebooks = list(op.get_bind().execute(phonebooks_query))
    phonebook_by_name = {(p.name, str(p.tenant_uuid)): p for p in phonebooks}
    phonebook_by_id = {p.id: p for p in phonebooks}
    phonebook_uuid_map = {}
    for row in op.get_bind().execute(phonebook_sources_query):
        if 'phonebook_uuid' in row.extra_fields:
            phonebook_uuid = str(row.extra_fields['phonebook_uuid'])
            phonebook = next(
                (p for p in phonebooks if str(p.uuid) == phonebook_uuid), None
            )
            if phonebook:
                phonebook_uuid_map[row.uuid] = row.extra_fields['phonebook_uuid']
            else:
                print(
                    f'phonebook(uuid={phonebook_uuid}) not found for source {row.uuid}. Future migration might delete it.'
                )
        elif 'phonebook_id' in row.extra_fields:
            phonebook_id = row.extra_fields['phonebook_id']
            try:
                phonebook = phonebook_by_id[phonebook_id]
                phonebook_uuid_map[row.uuid] = phonebook.uuid
            except KeyError:
                print(
                    f'phonebook(id={phonebook_id}) not found for source {row.uuid}. Future migration might delete it.'
                )
                continue
        else:
            try:
                phonebook = phonebook_by_name[(row.name, str(row.tenant_uuid))]
                phonebook_uuid_map[row.uuid] = phonebook.uuid
            except KeyError:
                print(
                    f'could not map source {row.uuid} to a phonebook. Future migration might delete it.'
                )
                continue

    if phonebook_uuid_map:
        phonebook_sources_update = (
            source_table.update()
            .where(
                source_table.c.uuid == sa.bindparam('_source_uuid'),
            )
            .values(
                phonebook_uuid=sa.bindparam('_phonebook_uuid'),
                extra_fields=(
                    sa.cast(source_table.c.extra_fields, postgresql.JSONB)
                    - 'phonebook_uuid'
                ),
            )
        )
        op.get_bind().execute(
            phonebook_sources_update,
            [
                {'_source_uuid': uuid, '_phonebook_uuid': phonebook_uuid}
                for uuid, phonebook_uuid in phonebook_uuid_map.items()
            ],
        )


def downgrade():
    op.get_bind().execute(
        source_table.update()
        .where(
            source_table.c.phonebook_uuid.isnot(None),
        )
        .values(
            extra_fields=sa.func.jsonb_set(
                sa.cast(source_table.c.extra_fields, postgresql.JSONB),
                ['phonebook_uuid'],
                sa.func.to_jsonb(source_table.c.phonebook_uuid),
            )
        )
    )
    op.drop_constraint('dird_source_phonebook_fkey', 'dird_source', type_='foreignkey')
    op.drop_constraint(
        'dird_phonebook_tenant_uuid_idx', 'dird_phonebook', type_='unique'
    )
    op.drop_column('dird_source', 'phonebook_uuid')
