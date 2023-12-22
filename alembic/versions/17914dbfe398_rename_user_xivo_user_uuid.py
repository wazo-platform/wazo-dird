# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

"""rename user.xivo_user_uuid

Revision ID: 17914dbfe398
Revises: 07e71f4c5437

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '17914dbfe398'
down_revision = '07e71f4c5437'


def upgrade():
    op.drop_constraint(
        'dird_contact_user_uuid_fkey', 'dird_contact', type_='foreignkey'
    )
    op.drop_constraint(
        'dird_favorite_user_uuid_fkey', 'dird_favorite', type_='foreignkey'
    )
    op.drop_constraint('dird_favorite_pkey', 'dird_favorite', type_='primary')

    op.alter_column(
        'dird_user',
        'xivo_user_uuid',
        existing_type=sa.String(38),
        type_=sa.String(36),
        new_column_name='user_uuid',
    )
    op.alter_column(
        'dird_contact', 'user_uuid', existing_type=sa.String(38), type_=sa.String(36)
    )
    op.alter_column(
        'dird_favorite', 'user_uuid', existing_type=sa.String(38), type_=sa.String(36)
    )

    op.create_foreign_key(
        'dird_contact_user_uuid_fkey',
        'dird_contact',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
    )
    op.create_foreign_key(
        'dird_favorite_user_uuid_fkey',
        'dird_favorite',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
    )

    op.create_primary_key(
        'dird_favorite_pkey',
        'dird_favorite',
        ['source_uuid', 'contact_id', 'user_uuid'],
    )


def downgrade():
    op.drop_constraint(
        'dird_contact_user_uuid_fkey', 'dird_contact', type_='foreignkey'
    )
    op.drop_constraint(
        'dird_favorite_user_uuid_fkey', 'dird_favorite', type_='foreignkey'
    )
    op.drop_constraint('dird_favorite_pkey', 'dird_favorite', type_='primary')

    op.alter_column(
        'dird_user',
        'user_uuid',
        existing_type=sa.String(36),
        type_=sa.String(38),
        new_column_name='xivo_user_uuid',
    )
    op.alter_column(
        'dird_favorite', 'user_uuid', existing_type=sa.String(36), type_=sa.String(38)
    )
    op.alter_column(
        'dird_contact', 'user_uuid', existing_type=sa.String(36), type_=sa.String(38)
    )

    op.create_primary_key(
        'dird_favorite_pkey',
        'dird_favorite',
        ['source_uuid', 'contact_id', 'user_uuid'],
    )
    op.create_foreign_key(
        'dird_favorite_user_uuid_fkey',
        'dird_favorite',
        'dird_user',
        ['user_uuid'],
        ['xivo_user_uuid'],
    )
    op.create_foreign_key(
        'dird_contact_user_uuid_fkey',
        'dird_contact',
        'dird_user',
        ['user_uuid'],
        ['xivo_user_uuid'],
    )
