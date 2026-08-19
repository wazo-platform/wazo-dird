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

    duplicates = connection.execute(
        sa.select(sa.func.count()).select_from(
            sa.select(sa.literal(1))
            .select_from(_profile_service_source)
            .group_by(
                _profile_service_source.c.profile_service_uuid,
                _profile_service_source.c.source_uuid,
            )
            .having(sa.func.count() > 1)
            .subquery()
        )
    ).scalar()
    if duplicates:
        raise RuntimeError(
            f'{duplicates} duplicate (profile_service_uuid, source_uuid) '
            'pair(s) in dird_profile_service_source; BUG-455 assumed this '
            'never happens. Investigate before adding this primary key.'
        )

    tenant_violations = connection.execute(
        sa.select(sa.func.count())
        .select_from(_profile_service_source)
        .where(
            _profile_service_source.c.profile_tenant_uuid
            != _profile_service_source.c.source_tenant_uuid
        )
    ).scalar()
    if tenant_violations:
        raise RuntimeError(
            f'{tenant_violations} row(s) in dird_profile_service_source have '
            'profile_tenant_uuid != source_tenant_uuid; BUG-455 assumed this '
            'never happens. Investigate before adding this constraint.'
        )

    op.execute(
        'ALTER TABLE dird_profile_service_source '
        'ADD CONSTRAINT dird_profile_service_source_pkey '
        'PRIMARY KEY (profile_service_uuid, source_uuid)'
    )
    op.execute(
        'ALTER TABLE dird_profile_service_source '
        'ADD CONSTRAINT dird_profile_service_source_check '
        'CHECK (profile_tenant_uuid = source_tenant_uuid)'
    )


def downgrade() -> None:
    op.execute(
        'ALTER TABLE dird_profile_service_source '
        'DROP CONSTRAINT dird_profile_service_source_check'
    )
    op.execute(
        'ALTER TABLE dird_profile_service_source '
        'DROP CONSTRAINT dird_profile_service_source_pkey'
    )
