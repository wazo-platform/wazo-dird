"""make contact key a text field

Revision ID: 4cf41a847a26
Revises: 1c6344eac1bd

"""

from alembic import op
from sqlalchemy.types import Text, String

# revision identifiers, used by Alembic.
revision = '4cf41a847a26'
down_revision = '1c6344eac1bd'


def upgrade():
    _change_type(Text)


def downgrade():
    _change_type(String(20))


def _change_type(t):
    op.alter_column('dird_contact_fields', 'name', type_=t)
