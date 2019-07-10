# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""add a uuid to the tenant table

Revision ID: 401aca548ddf
Revises: 1e0397088fa7

"""

from uuid import uuid4
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '401aca548ddf'
down_revision = '1e0397088fa7'

tenant_table_name = 'dird_tenant'
phonebook_table_name = 'dird_phonebook'
UUID_LENGTH = len(str(uuid4()))


def upgrade():
    op.add_column(
        tenant_table_name,
        sa.Column(
            'uuid',
            sa.String(UUID_LENGTH),
            nullable=False,
            server_default=sa.text('uuid_generate_v4()'),
        ),
    )
    op.add_column(
        phonebook_table_name, sa.Column('tenant_uuid', sa.String(UUID_LENGTH))
    )

    tenant_table = sa.sql.table(
        tenant_table_name, sa.sql.column('id'), sa.sql.column('uuid')
    )
    id_uuid_query = sa.sql.select([tenant_table.c.id, tenant_table.c.uuid])
    id_uuid_rows = op.get_bind().execute(id_uuid_query).fetchall()

    phonebook_table = sa.sql.table(
        phonebook_table_name, sa.sql.column('tenant_id'), sa.sql.column('tenant_uuid')
    )

    for id_, uuid in id_uuid_rows:
        op.execute(
            phonebook_table.update()
            .where(phonebook_table.c.tenant_id == id_)
            .values(tenant_uuid=uuid)
        )

    op.alter_column(phonebook_table_name, 'tenant_uuid', nullable=False)
    op.execute(
        'ALTER TABLE dird_phonebook DROP CONSTRAINT dird_phonebook_tenant_id_fkey CASCADE'
    )
    op.execute('ALTER TABLE dird_tenant DROP CONSTRAINT dird_tenant_pkey CASCADE')
    op.create_primary_key('dird_tenant_pkey', tenant_table_name, ['uuid'])
    op.create_foreign_key(
        'dird_phonebook_tenant_uuid_fkey',
        phonebook_table_name,
        'dird_tenant',
        ['tenant_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )
    op.create_unique_constraint(
        'dird_phonebook_name_tenant_uuid', phonebook_table_name, ['name', 'tenant_uuid']
    )
    op.drop_column(tenant_table_name, 'id')
    op.drop_column(phonebook_table_name, 'tenant_id')


def downgrade():
    pass
