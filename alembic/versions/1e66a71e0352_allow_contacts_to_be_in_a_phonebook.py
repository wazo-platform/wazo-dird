"""Allow contacts to be in a phonebook

Revision ID: 1e66a71e0352
Revises: 28e9ff92ed2

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '1e66a71e0352'
down_revision = '28e9ff92ed2'

constraint_name = 'dird_contact_hash_phonebook_id'
table_name = 'dird_contact'


def upgrade():
    op.alter_column(table_name, 'user_uuid', nullable=True)
    op.add_column(
        table_name,
        sa.Column(
            'phonebook_id',
            sa.Integer(),
            sa.ForeignKey('dird_phonebook.id', ondelete='CASCADE'),
        ),
    )
    op.create_unique_constraint(constraint_name, table_name, ['hash', 'phonebook_id'])


def downgrade():
    op.drop_constraint(constraint_name, table_name)
    op.drop_column(table_name, 'phonebook_id')
    op.alter_column(table_name, 'user_uuid', nullable=False)
