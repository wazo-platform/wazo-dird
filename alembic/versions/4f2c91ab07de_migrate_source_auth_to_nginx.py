"""migrate_source_auth_to_nginx

Revision ID: 4f2c91ab07de
Revises: 5a67556fbbf1

"""

import sqlalchemy as sa

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = '4f2c91ab07de'
down_revision = '5a67556fbbf1'

_table = sa.table(
    'dird_source',
    sa.column('uuid', sa.String),
    sa.column('extra_fields', sa.JSON),
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.select(_table)).fetchall()
    for row in rows:
        extra_fields = row.extra_fields
        if not isinstance(extra_fields, dict):
            continue
        auth = extra_fields.get('auth')
        if not isinstance(auth, dict):
            continue
        # sources pointing elsewhere are configured by the administrator
        if auth.get('host') != 'localhost' or auth.get('port') != 9497:
            continue
        auth['port'] = 80
        auth['prefix'] = '/api/auth'
        conn.execute(
            sa.update(_table)
            .where(_table.c.uuid == row.uuid)
            .values(extra_fields=extra_fields)
        )


def downgrade() -> None:
    pass
