"""migrate_profile_service_timeout_to_options

Revision ID: 5a67556fbbf1
Revises: 2adc8aff56ea

"""

import sqlalchemy as sa

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = '5a67556fbbf1'
down_revision = '2adc8aff56ea'

_table = sa.table(
    'dird_profile_service',
    sa.column('uuid', sa.String),
    sa.column('config', sa.JSON),
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.select(_table)).fetchall()
    for row in rows:
        config = row.config
        if not isinstance(config, dict) or 'timeout' not in config:
            continue
        top_level_timeout = config.pop('timeout', None)
        options = config.get('options') or {}
        if 'timeout' not in options:
            options['timeout'] = top_level_timeout
        config['options'] = options
        conn.execute(
            sa.update(_table).where(_table.c.uuid == row.uuid).values(config=config)
        )


def downgrade() -> None:
    pass
