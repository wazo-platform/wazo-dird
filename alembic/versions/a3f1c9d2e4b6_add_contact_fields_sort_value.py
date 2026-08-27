"""add_contact_fields_sort_value

Revision ID: a3f1c9d2e4b6
Revises: 30ae0fd93125

"""

import sqlalchemy as sa
from psycopg2.extras import execute_values
from unidecode import unidecode

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'a3f1c9d2e4b6'
down_revision = '30ae0fd93125'

TABLE_NAME = 'dird_contact_fields'
COLUMN_NAME = 'sort_value'
_BATCH_SIZE = 5000

_contact_fields = sa.table(
    TABLE_NAME,
    sa.column('id', sa.Integer),
    sa.column('value', sa.Text),
    sa.column('sort_value', sa.Text),
)


def upgrade() -> None:
    op.add_column(TABLE_NAME, sa.Column(COLUMN_NAME, sa.Text(), nullable=True))

    conn = op.get_bind()
    cursor = conn.connection.cursor()

    # Backfill in id-ordered batches so memory stays bounded on large tables.
    last_id = 0
    while True:
        rows = conn.execute(
            sa.select(_contact_fields.c.id, _contact_fields.c.value)
            .where(
                _contact_fields.c.id > last_id,
                _contact_fields.c.value.isnot(None),
            )
            .order_by(_contact_fields.c.id)
            .limit(_BATCH_SIZE)
        ).fetchall()
        if not rows:
            break
        payload = [(contact_id, unidecode(value)) for contact_id, value in rows]
        execute_values(
            cursor,
            f'UPDATE {TABLE_NAME} AS t SET {COLUMN_NAME} = v.{COLUMN_NAME} '
            f'FROM (VALUES %s) AS v(id, {COLUMN_NAME}) WHERE t.id = v.id',
            payload,
            template='(%s, %s)',
            page_size=_BATCH_SIZE,
        )
        last_id = rows[-1][0]


def downgrade() -> None:
    op.drop_column(TABLE_NAME, COLUMN_NAME)
