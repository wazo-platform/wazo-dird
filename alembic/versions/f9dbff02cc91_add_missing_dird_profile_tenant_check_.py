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
    violations = connection.execute(
        sa.select(sa.func.count())
        .select_from(_profile)
        .where(_profile.c.tenant_uuid != _profile.c.display_tenant_uuid)
    ).scalar()
    if violations:
        raise RuntimeError(
            f'{violations} row(s) in dird_profile have tenant_uuid != '
            'display_tenant_uuid; BUG-455 assumed this never happens. '
            'Investigate before adding this constraint.'
        )

    # Unnamed: Postgres auto-names it dird_profile_check, matching the
    # unnamed CheckConstraint already in wazo_dird/database/models.py.
    op.execute('ALTER TABLE dird_profile ADD CHECK (tenant_uuid = display_tenant_uuid)')


def downgrade() -> None:
    op.execute('ALTER TABLE dird_profile DROP CONSTRAINT dird_profile_check')
