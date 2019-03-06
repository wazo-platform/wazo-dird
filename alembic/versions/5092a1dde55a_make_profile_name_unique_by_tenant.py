"""make profile name unique by tenant

Revision ID: 5092a1dde55a
Revises: b399551c3351

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '5092a1dde55a'
down_revision = 'b399551c3351'


table_name = 'dird_profile'
constraint_name = 'dird_profile_tenant_name'


def upgrade():
    op.create_unique_constraint(constraint_name, table_name, ['tenant_uuid', 'name'])


def downgrade():
    op.drop_constraint(constraint_name, table_name)
