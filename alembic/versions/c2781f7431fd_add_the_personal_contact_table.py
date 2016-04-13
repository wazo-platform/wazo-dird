"""add the personal contact table

Revision ID: c2781f7431fd
Revises: d237d33088c6

"""

# revision identifiers, used by Alembic.
revision = 'c2781f7431fd'
down_revision = 'd237d33088c6'

from alembic import op
from sqlalchemy.schema import Column
from sqlalchemy import String, ForeignKey

table_name = 'dird_personal_contact'


def upgrade():
    op.create_table(
        table_name,
        Column('contact_uuid', String(38), ForeignKey('dird_contact.uuid', ondelete='CASCADE'), primary_key=True),
        Column('user_uuid', String(38), ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE')),
    )


def downgrade():
    op.drop_table(table_name)
