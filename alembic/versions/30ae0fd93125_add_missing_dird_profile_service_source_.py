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
    sa.column('ctid'),
)


def upgrade() -> None:
    connection = op.get_bind()

    # The composite FKs use MATCH SIMPLE, so a NULL in either key column
    # escapes FK enforcement; such orphans would make the primary key
    # creation below abort.
    connection.execute(
        _profile_service_source.delete().where(
            sa.or_(
                _profile_service_source.c.profile_service_uuid.is_(None),
                _profile_service_source.c.source_uuid.is_(None),
            )
        )
    )

    # profile_tenant_uuid/source_tenant_uuid are each pinned by an FK to a
    # single parent row, so duplicates here are exact duplicates; keep one
    # per pair via ctid.
    keep = sa.select(sa.func.min(_profile_service_source.c.ctid)).group_by(
        _profile_service_source.c.profile_service_uuid,
        _profile_service_source.c.source_uuid,
    )
    connection.execute(
        _profile_service_source.delete().where(
            _profile_service_source.c.ctid.notin_(keep)
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
