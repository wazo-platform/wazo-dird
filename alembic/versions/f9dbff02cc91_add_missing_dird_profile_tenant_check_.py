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
    sa.column('display_tenant_uuid', sa.String),
)


def upgrade() -> None:
    connection = op.get_bind()
    # Deletes rather than nulling display_uuid/display_tenant_uuid:
    # build_display() in wazo_dird/helpers.py can't handle a None display.
    connection.execute(
        _profile.delete().where(
            _profile.c.tenant_uuid != _profile.c.display_tenant_uuid
        )
    )

    op.create_check_constraint(
        'dird_profile_check', 'dird_profile', 'tenant_uuid = display_tenant_uuid'
    )


def downgrade() -> None:
    op.drop_constraint('dird_profile_check', 'dird_profile', type_='check')
