"""restrict_wazo_source_first_matched_columns

Revision ID: bcee44e583d9
Revises: d4b8f0c61e57

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'bcee44e583d9'
down_revision = 'd4b8f0c61e57'

BACKEND = 'wazo'
SUPPORTED_COLUMNS = ('exten', 'mobile_phone_number')

_source = sa.table(
    'dird_source',
    sa.column('uuid', sa.String),
    sa.column('backend', sa.Text),
    sa.column('first_matched_columns', ARRAY(sa.Text)),
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(_source.c.uuid, _source.c.first_matched_columns).where(
            _source.c.backend == BACKEND,
            _source.c.first_matched_columns.isnot(None),
        )
    ).fetchall()

    for row in rows:
        kept = [
            column
            for column in row.first_matched_columns
            if column in SUPPORTED_COLUMNS
        ]
        if kept == list(row.first_matched_columns):
            continue
        conn.execute(
            sa.update(_source)
            .where(_source.c.uuid == row.uuid)
            .values(first_matched_columns=kept)
        )


def downgrade() -> None:
    pass
