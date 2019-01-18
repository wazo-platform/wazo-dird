# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+
"""add the source.backend column

Revision ID: 0279b94ee7c6
Revises: 25e9a6782cac

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0279b94ee7c6'
down_revision = '25e9a6782cac'


def upgrade():
    table_name = 'dird_source'
    column_name = 'backend'

    op.add_column(
        table_name,
        sa.Column(column_name, sa.Text(), nullable=False, server_default='migration'),
    )
    op.alter_column(table_name, column_name, nullable=False, server_default=None)


def downgrade():
    pass
