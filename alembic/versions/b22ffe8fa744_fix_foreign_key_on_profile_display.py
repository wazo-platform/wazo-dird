"""fix foreign key on profile display

Revision ID: b22ffe8fa744
Revises: 5092a1dde55a

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b22ffe8fa744'
down_revision = '5092a1dde55a'


def upgrade():
    op.add_column('dird_profile', sa.Column('display_tenant_uuid', sa.String(36)))
    profile_table = sa.sql.table(
        'dird_profile',
        sa.sql.column('tenant_uuid'),
        sa.sql.column('display_tenant_uuid'),
    )
    op.execute(
        profile_table.update().values(display_tenant_uuid=profile_table.c.tenant_uuid)
    )

    op.create_unique_constraint(
        'dird_display_uuid_tenant', 'dird_display', ['uuid', 'tenant_uuid']
    )
    op.create_foreign_key(
        'dird_profile_display_uuid_tenant_fkey',
        'dird_profile',
        'dird_display',
        ['display_uuid', 'display_tenant_uuid'],
        ['uuid', 'tenant_uuid'],
        ondelete='SET NULL',
    )
    op.drop_constraint('dird_profile_display_uuid_fkey', 'dird_profile')


def downgrade():
    op.create_foreign_key(
        'dird_profile_display_uuid_fkey',
        'dird_profile',
        'dird_display',
        ['display_uuid'],
        ['uuid'],
    )
    op.drop_constraint('dird_profile_display_uuid_tenant_fkey', 'dird_profile')
    op.drop_constraint('dird_display_uuid_tenant', 'dird_display')
    op.drop_column('dird_profile', 'display_tenant_uuid')
