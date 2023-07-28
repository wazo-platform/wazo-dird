"""Added uuid column to phonebook table

Revision ID: bb2cd24f0500
Revises: 9c426a2c7e59

"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'bb2cd24f0500'
down_revision = '9c426a2c7e59'

dird_contact_table = sa.table(
    'dird_contact',
    sa.column('phonebook_id'),
    sa.column('phonebook_uuid'),
)
dird_phonebook_table = sa.table(
    'dird_phonebook',
    sa.column('id'),
    sa.column('uuid'),
)


def update_contact_phonebook_uuid():
    return dird_contact_table.update().values(
        phonebook_uuid=sa.select([dird_phonebook_table.c.uuid]).where(
            dird_phonebook_table.c.id == dird_contact_table.c.phonebook_id
        )
    )


def update_contact_phonebook_id():
    return dird_contact_table.update().values(
        phonebook_id=sa.select([dird_phonebook_table.c.id]).where(
            dird_phonebook_table.c.uuid == dird_contact_table.c.phonebook_uuid
        )
    )


def sequence_exists(conn, seq_name):
    result = conn.execute('select sequencename from pg_sequences')
    names = list(seq for (seq,) in result)
    return seq_name in names


def get_highest_phonebook_id(conn) -> int | None:
    return conn.execute(
        dird_phonebook_table.select([sa.func.max(dird_phonebook_table.c.id)])
    ).scalar()


def upgrade():
    # remove obsolete foreign key column 'phonebook_id' from dird_contact
    op.drop_constraint(
        'dird_contact_phonebook_id_fkey', 'dird_contact', type_='foreignkey'
    )

    # add new primary key column uuid to dird_phonebook table
    op.add_column(
        'dird_phonebook',
        sa.Column(
            'uuid',
            postgresql.UUID(),
            server_default=sa.text('uuid_generate_v4()'),
            nullable=False,
        ),
    )
    # replace integer primary key 'id' with uuid
    op.drop_constraint('dird_phonebook_pkey', 'dird_phonebook', type_='primary')
    op.create_primary_key('dird_phonebook_pkey', 'dird_phonebook', ['uuid'])

    # make sure existing autoincremented id column remains functional
    op.create_unique_constraint('dird_phonebook_id', 'dird_phonebook', ['id'])
    if not sequence_exists(op.get_bind(), 'dird_phonebook_id_seq'):
        sequence = (
            sa.Sequence(
                'dird_phonebook_id_seq',
                start=get_highest_phonebook_id(op.get_bind()) or 1,
            ),
        )
        op.execute(sa.schema.CreateSequence(sequence))

    op.alter_column(
        'dird_phonebook',
        'id',
        server_default=sa.text('nextval(\'dird_phonebook_id_seq\'::regclass)'),
        nullable=False,
    )

    # add new foreign key to dird_contact table referencing dird_phonebook uuid column
    op.add_column(
        'dird_contact',
        sa.Column(
            'phonebook_uuid',
            postgresql.UUID(),
            nullable=True,
        ),
    )
    op.execute(update_contact_phonebook_uuid())
    op.create_foreign_key(
        'dird_contact_phonebook_uuid_fkey',
        'dird_contact',
        'dird_phonebook',
        ['phonebook_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )
    op.create_index(
        'dird_contact__idx__phonebook_uuid', 'dird_contact', ['phonebook_uuid']
    )
    op.create_unique_constraint(
        'dird_contact_hash_phonebook_uuid', 'dird_contact', ['phonebook_uuid', 'hash']
    )

    # remove obsolete constraints, index and column in dird_contact
    op.drop_constraint('dird_contact_hash_phonebook_id', 'dird_contact', type_='unique')
    op.drop_index('dird_contact__idx__phonebook_id', 'dird_contact')
    op.drop_column('dird_contact', 'phonebook_id')


def downgrade():
    # add back phonebook_id foreign key column to dird_contact
    op.add_column(
        'dird_contact', sa.Column('phonebook_id', postgresql.INTEGER(), nullable=True)
    )
    op.get_bind().execute(update_contact_phonebook_id())

    op.create_foreign_key(
        'dird_contact_phonebook_id_fkey',
        'dird_contact',
        'dird_phonebook',
        ['phonebook_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('dird_contact__idx__phonebook_id', 'dird_contact', ['phonebook_id'])
    # remove foreign key to dird_phonebook uuid column
    op.drop_constraint(
        'dird_contact_phonebook_uuid_fkey', 'dird_contact', type_='foreignkey'
    )
    op.drop_index('dird_contact__idx__phonebook_uuid', 'dird_contact')
    op.drop_constraint(
        'dird_contact_hash_phonebook_uuid', 'dird_contact', type_='unique'
    )
    op.drop_column('dird_contact', 'phonebook_uuid')

    # remove uuid primary key from dird_phonebook, replace with id column
    op.drop_constraint('dird_phonebook_pkey', 'dird_phonebook', type_='primary')
    op.create_primary_key('dird_phonebook_pkey', 'dird_phonebook', ['id'])
    op.drop_column('dird_phonebook', 'uuid')
