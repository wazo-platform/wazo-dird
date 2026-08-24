"""add missing dird_profile tenant check constraint

Revision ID: f9dbff02cc91
Revises: 52869e467b80

"""

import sqlalchemy as sa

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'f9dbff02cc91'
down_revision = '52869e467b80'

_profile = sa.table(
    'dird_profile',
    sa.column('tenant_uuid', sa.String),
    sa.column('display_uuid', sa.String),
    sa.column('display_tenant_uuid', sa.String),
)


def upgrade() -> None:
    connection = op.get_bind()
    # display_tenant_uuid only mirrors tenant_uuid for the FK below; a
    # mismatch means the display link is wrong, not the profile itself.
    connection.execute(
        _profile.update()
        .where(_profile.c.tenant_uuid != _profile.c.display_tenant_uuid)
        .values(display_uuid=None, display_tenant_uuid=None)
    )

    op.create_check_constraint(
        'dird_profile_check', 'dird_profile', 'tenant_uuid = display_tenant_uuid'
    )


def downgrade() -> None:
    op.drop_constraint('dird_profile_check', 'dird_profile', type_='check')
