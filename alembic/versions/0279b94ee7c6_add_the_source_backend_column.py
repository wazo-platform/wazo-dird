# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""add the source.backend column

Revision ID: 0279b94ee7c6
Revises: 25e9a6782cac

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '0279b94ee7c6'
down_revision = '25e9a6782cac'
table_name = 'dird_source'
column_name = 'backend'


def upgrade():
    op.add_column(
        table_name,
        sa.Column(column_name, sa.Text(), nullable=False, server_default='migration'),
    )
    op.alter_column(table_name, column_name, nullable=False, server_default=None)


def downgrade():
    op.drop_column(table_name, column_name)
