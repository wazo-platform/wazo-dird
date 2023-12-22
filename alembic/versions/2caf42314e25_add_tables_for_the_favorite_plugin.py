"""add tables for the favorite plugin

Revision ID: 2caf42314e25
Revises: 4cf41a847a26

"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.schema import Column

from alembic import op

# revision identifiers, used by Alembic.
revision = '2caf42314e25'
down_revision = '4cf41a847a26'


def upgrade():
    op.create_table(
        'dird_source',
        Column('id', Integer(), primary_key=True),
        Column('name', Text(), nullable=False, unique=True),
    )
    op.create_table(
        'dird_favorite',
        Column(
            'source_id',
            Integer(),
            ForeignKey('dird_source.id', ondelete='CASCADE'),
            primary_key=True,
        ),
        Column('contact_id', Text(), primary_key=True),
        Column(
            'user_uuid',
            String(38),
            ForeignKey('dird_user.xivo_user_uuid', ondelete='CASCADE'),
            primary_key=True,
        ),
    )


def downgrade():
    op.drop_table('dird_favorite')
    op.drop_table('dird_source')
