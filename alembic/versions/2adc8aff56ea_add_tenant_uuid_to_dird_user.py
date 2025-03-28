"""add tenant_uuid to dird_user

Revision ID: 2adc8aff56ea
Revises: 04c5c746a50b

"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '2adc8aff56ea'
down_revision = '04c5c746a50b'

UUID_LENGTH = len(str(uuid4()))
user_table_name = 'dird_user'


def upgrade():
    op.add_column(
        user_table_name,
        sa.Column(
            'tenant_uuid',
            sa.String(UUID_LENGTH),
            sa.ForeignKey('dird_tenant.uuid', ondelete='CASCADE'),
        ),
    )
    op.create_index(
        f'{user_table_name}__idx__tenant_uuid',
        user_table_name,
        ['tenant_uuid'],
    )


def downgrade():
    op.drop_column(user_table_name, 'tenant_uuid')
    op.drop_index(f'{user_table_name}__idx__tenant_uuid')
