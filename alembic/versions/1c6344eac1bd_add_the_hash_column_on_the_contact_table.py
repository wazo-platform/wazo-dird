"""add the hash column on the contact table

Revision ID: 1c6344eac1bd
Revises: 38485dfa4e41

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1c6344eac1bd'
down_revision = '38485dfa4e41'

constraint_name = 'dird_contact_hash_user_uuid'
table_name = 'dird_contact'
column_name = 'hash'


def upgrade():
    op.add_column(table_name, sa.Column(column_name,
                                        sa.String(40),
                                        nullable=False))
    op.create_unique_constraint(constraint_name, table_name, [column_name, 'user_uuid'])


def downgrade():
    op.drop_constraint(constraint_name, table_name)
    op.drop_column(table_name, column_name)
