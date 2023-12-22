"""add the contact table

Revision ID: b0df0bc0ce37
Revises: None

"""

from sqlalchemy import String, text
from sqlalchemy.schema import Column

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b0df0bc0ce37'
down_revision = None

table_name = 'dird_contact'


def upgrade():
    op.create_table(
        table_name,
        Column(
            'uuid',
            String(38),
            server_default=text('uuid_generate_v4()'),
            primary_key=True,
        ),
    )


def downgrade():
    op.drop_table(table_name)
