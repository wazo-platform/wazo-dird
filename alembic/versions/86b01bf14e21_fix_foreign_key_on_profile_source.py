"""fix foreign key on profile source

Revision ID: 86b01bf14e21
Revises: b22ffe8fa744

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '86b01bf14e21'
down_revision = 'b22ffe8fa744'


def upgrade():
    # Create the foreign tenant_uuid columns
    # dird_profile_service.profile_tenant_uuid
    # dird_profile_service_source.profile_tenant_uuid
    # dird_profile_service_source.source_tenant_uuid
    op.add_column(
        'dird_profile_service', sa.Column('profile_tenant_uuid', sa.String(36))
    )
    op.add_column(
        'dird_profile_service_source', sa.Column('profile_tenant_uuid', sa.String(36))
    )
    op.add_column(
        'dird_profile_service_source', sa.Column('source_tenant_uuid', sa.String(36))
    )

    profile_table = sa.sql.table(
        'dird_profile', sa.sql.column('uuid'), sa.sql.column('tenant_uuid')
    )
    profile_service_table = sa.sql.table(
        'dird_profile_service',
        sa.sql.column('uuid'),
        sa.sql.column('profile_uuid'),
        sa.sql.column('profile_tenant_uuid'),
    )
    profile_service_source_table = sa.sql.table(
        'dird_profile_service_source',
        sa.sql.column('profile_service_uuid'),
        sa.sql.column('profile_tenant_uuid'),
        sa.sql.column('source_uuid'),
        sa.sql.column('source_tenant_uuid'),
    )
    source_table = sa.sql.table(
        'dird_source', sa.sql.column('uuid'), sa.sql.column('tenant_uuid')
    )

    profile_to_tenant_query = sa.sql.select(
        [profile_table.c.uuid, profile_table.c.tenant_uuid]
    )
    rows = op.get_bind().execute(profile_to_tenant_query).fetchall()
    profile_to_tenant = {row.uuid: row.tenant_uuid for row in rows}
    for uuid, tenant_uuid in profile_to_tenant.items():
        op.execute(
            profile_service_table.update()
            .where(profile_service_table.c.profile_uuid == uuid)
            .values(profile_tenant_uuid=tenant_uuid)
        )

    profile_service_to_tenant_query = sa.sql.select(
        [profile_service_table.c.uuid, profile_service_table.c.profile_tenant_uuid]
    )
    rows = op.get_bind().execute(profile_service_to_tenant_query).fetchall()
    profile_service_to_tenant = {row.uuid: row.profile_tenant_uuid for row in rows}
    for uuid, tenant_uuid in profile_service_to_tenant.items():
        op.execute(
            profile_service_source_table.update()
            .where(profile_service_source_table.c.profile_service_uuid == uuid)
            .values(profile_tenant_uuid=tenant_uuid)
        )

    source_to_tenant_query = sa.sql.select(
        [source_table.c.uuid, source_table.c.tenant_uuid]
    )
    rows = op.get_bind().execute(source_to_tenant_query).fetchall()
    source_to_tenant = {row.uuid: row.tenant_uuid for row in rows}
    for uuid, tenant_uuid in source_to_tenant.items():
        op.execute(
            profile_service_source_table.update()
            .where(profile_service_source_table.c.source_uuid == uuid)
            .values(source_tenant_uuid=tenant_uuid)
        )

    # Make the tenant/uuid pair unique
    op.create_unique_constraint(
        'dird_profile_uuid_tenant', 'dird_profile', ['uuid', 'tenant_uuid']
    )
    op.create_unique_constraint(
        'dird_profile_service_uuid_tenant',
        'dird_profile_service',
        ['uuid', 'profile_tenant_uuid'],
    )
    op.create_unique_constraint(
        'dird_source_uuid_tenant', 'dird_source', ['uuid', 'tenant_uuid']
    )

    # Create new foreign keys using the foreign tenant_uuid keys
    op.create_foreign_key(
        'dird_profile_service_profile_uuid_tenant_fkey',
        'dird_profile_service',
        'dird_profile',
        ['profile_uuid', 'profile_tenant_uuid'],
        ['uuid', 'tenant_uuid'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'dird_profile_service_source_profile_service_uuid_tenant_fkey',
        'dird_profile_service_source',
        'dird_profile_service',
        ['profile_service_uuid', 'profile_tenant_uuid'],
        ['uuid', 'profile_tenant_uuid'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'dird_profile_service_source_source_uuid_tenant_fkey',
        'dird_profile_service_source',
        'dird_source',
        ['source_uuid', 'source_tenant_uuid'],
        ['uuid', 'tenant_uuid'],
        ondelete='CASCADE',
    )

    # Drop the old foreign keys
    op.drop_constraint('dird_profile_service_profile_uuid_fkey', 'dird_profile_service')
    op.drop_constraint(
        'dird_profile_service_source_profile_service_uuid_fkey',
        'dird_profile_service_source',
    )
    op.drop_constraint(
        'dird_profile_service_source_source_uuid_fkey', 'dird_profile_service_source'
    )


def downgrade():
    # Recreate the old FK
    op.create_foreign_key(
        'dird_profile_service_profile_uuid_fkey',
        'dird_profile_service',
        'dird_profile',
        ['profile_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'dird_profile_service_source_profile_service_uuid_fkey',
        'dird_profile_service_source',
        'dird_profile_service',
        ['profile_service_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'dird_profile_service_source_source_uuid_fkey',
        'dird_profile_service_source',
        'dird_source',
        ['source_uuid'],
        ['uuid'],
        ondelete='CASCADE',
    )

    # Remove the new FK
    op.drop_constraint(
        'dird_profile_service_profile_uuid_tenant_fkey', 'dird_profile_service'
    )
    op.drop_constraint(
        'dird_profile_service_source_profile_service_uuid_tenant_fkey',
        'dird_profile_service_source',
    )
    op.drop_constraint(
        'dird_profile_service_source_source_uuid_tenant_fkey',
        'dird_profile_service_source',
    )

    # Remove the unique constraints
    op.drop_constraint('dird_profile_uuid_tenant', 'dird_profile')
    op.drop_constraint('dird_profile_service_uuid_tenant', 'dird_profile_service')
    op.drop_constraint('dird_source_uuid_tenant', 'dird_source')

    # Drop the columns
    op.drop_column('dird_profile_service', 'profile_tenant_uuid')
    op.drop_column('dird_profile_service_source', 'profile_tenant_uuid')
    op.drop_column('dird_profile_service_source', 'source_tenant_uuid')
