"""add the user table

Revision ID: d237d33088c6
Revises: b0df0bc0ce37

"""

# revision identifiers, used by Alembic.
revision = 'd237d33088c6'
down_revision = 'b0df0bc0ce37'

from alembic import op
from sqlalchemy.schema import Column
from sqlalchemy import String

table_name = 'dird_user'


def upgrade():
    op.create_table(table_name,
                    Column('xivo_user_uuid', String(38), primary_key=True))


def downgrade():
    op.drop_table(table_name)
