"""add the fields table

Revision ID: 38485dfa4e41
Revises: 265d68f9c337

"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from alembic import op

# revision identifiers, used by Alembic.
revision = '38485dfa4e41'
down_revision = '265d68f9c337'

table_name = 'dird_contact_fields'
name_index = f'{table_name}_name_idx'
value_index = f'{table_name}_value_idx'


def upgrade():
    op.create_table(
        table_name,
        Column('id', Integer, primary_key=True),
        Column('name', String(20), nullable=False, index=True),
        Column('value', Text(), index=True),
        Column(
            'contact_uuid',
            String(38),
            ForeignKey('dird_contact.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table(table_name)
