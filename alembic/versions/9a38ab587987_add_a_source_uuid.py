# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""add a source uuid

Revision ID: 9a38ab587987
Revises: a3d1fa16da32

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '9a38ab587987'
down_revision = 'a3d1fa16da32'

favorite_table_name = 'dird_favorite'
source_table_name = 'dird_source'
UUID_LENGTH = len(str(uuid4()))


def upgrade():
    op.add_column(
        source_table_name,
        sa.Column(
            'uuid',
            sa.String(UUID_LENGTH),
            nullable=False,
            server_default=sa.text('uuid_generate_v4()'),
        )
    )
    op.add_column(
        favorite_table_name,
        sa.Column(
            'source_uuid',
            sa.String(UUID_LENGTH),
        )
    )

    source_table = sql.table(
        source_table_name,
        sql.column('id'),
        sql.column('uuid'),
    )
    id_uuid_query = sql.select([source_table.c.id, source_table.c.uuid])
    id_uuid_rows = op.get_bind().execute(id_uuid_query).fetchall()

    favorite_table = sql.table(
        favorite_table_name,
        sql.column('source_id'),
        sql.column('source_uuid'),
    )
    for id_, uuid in id_uuid_rows:
        op.execute(
            favorite_table
            .update()
            .where(favorite_table.c.source_id == id_)
            .values(source_uuid=uuid)
        )
    op.alter_column(favorite_table_name, 'source_uuid', nullable=False)

    op.execute('ALTER TABLE dird_favorite DROP CONSTRAINT dird_favorite_pkey CASCADE')
    op.execute('ALTER TABLE dird_favorite DROP CONSTRAINT dird_favorite_source_id_fkey CASCADE')
    op.execute('ALTER TABLE dird_source DROP CONSTRAINT dird_source_pkey CASCADE')
    op.create_primary_key(
        'dird_source_pkey',
        source_table_name,
        ['uuid'],
    )
    op.create_primary_key(
        'dird_favorite_pkey',
        favorite_table_name,
        ['source_uuid', 'contact_id', 'user_uuid'],
    )
    op.create_foreign_key(
        'dird_favorite_source_uuid_fkey',
        'dird_favorite',
        'dird_source',
        ['source_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )
    op.drop_column(source_table_name, 'id')
    op.drop_column(favorite_table_name, 'source_id')


def downgrade():
    pass
