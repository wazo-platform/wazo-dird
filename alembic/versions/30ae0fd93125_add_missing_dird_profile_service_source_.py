"""add missing dird_profile_service_source constraints

Revision ID: 30ae0fd93125
Revises: f9dbff02cc91

"""

import sqlalchemy as sa

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = '30ae0fd93125'
down_revision = 'f9dbff02cc91'

_profile_service_source = sa.table(
    'dird_profile_service_source',
    sa.column('profile_service_uuid', sa.String),
    sa.column('source_uuid', sa.String),
    sa.column('profile_tenant_uuid', sa.String),
    sa.column('source_tenant_uuid', sa.String),
)


def upgrade() -> None:
    connection = op.get_bind()

    # profile_tenant_uuid/source_tenant_uuid are each pinned by an FK to a
    # single parent row, so duplicates here are exact duplicates; keep one
    # per pair via ctid.
    connection.execute(
        sa.text(
            'DELETE FROM dird_profile_service_source a '
            'USING dird_profile_service_source b '
            'WHERE a.ctid < b.ctid '
            'AND a.profile_service_uuid = b.profile_service_uuid '
            'AND a.source_uuid = b.source_uuid'
        )
    )

    connection.execute(
        _profile_service_source.delete().where(
            _profile_service_source.c.profile_tenant_uuid
            != _profile_service_source.c.source_tenant_uuid
        )
    )

    op.create_primary_key(
        'dird_profile_service_source_pkey',
        'dird_profile_service_source',
        ['profile_service_uuid', 'source_uuid'],
    )
    op.create_check_constraint(
        'dird_profile_service_source_check',
        'dird_profile_service_source',
        'profile_tenant_uuid = source_tenant_uuid',
    )


def downgrade() -> None:
    op.drop_constraint(
        'dird_profile_service_source_check',
        'dird_profile_service_source',
        type_='check',
    )
    op.drop_constraint(
        'dird_profile_service_source_pkey',
        'dird_profile_service_source',
        type_='primary',
    )
