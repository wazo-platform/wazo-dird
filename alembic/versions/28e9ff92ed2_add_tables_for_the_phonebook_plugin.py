"""add tables for the phonebook plugin

Revision ID: 28e9ff92ed2
Revises: 2caf42314e25

"""

from alembic import op

from sqlalchemy.schema import Column
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

# revision identifiers, used by Alembic.
revision = '28e9ff92ed2'
down_revision = '2caf42314e25'


def upgrade():
    op.create_table(
        'dird_tenant',
        Column('id', Integer(), primary_key=True),
        Column(
            'name',
            String(255),
            CheckConstraint("name != ''"),
            unique=True,
            nullable=False,
        ),
    )
    op.create_table(
        'dird_phonebook',
        Column('id', Integer(), primary_key=True),
        Column('name', String(255), CheckConstraint("name != ''"), nullable=False),
        Column('description', Text()),
        Column('tenant_id', Integer(), ForeignKey('dird_tenant.id')),
        UniqueConstraint('name', 'tenant_id'),
    )


def downgrade():
    op.drop_table('dird_phonebook')
    op.drop_table('dird_tenant')
