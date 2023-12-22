"""add contact relation

Revision ID: 265d68f9c337
Revises: d237d33088c6

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '265d68f9c337'
down_revision = 'd237d33088c6'

table_name = 'dird_contact'
column_name = 'user_uuid'


def upgrade():
    op.add_column(
        table_name,
        sa.Column(
            column_name,
            sa.String(38),
            sa.ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column(table_name, column_name)
