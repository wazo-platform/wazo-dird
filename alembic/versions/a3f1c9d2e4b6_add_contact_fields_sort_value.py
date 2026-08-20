"""add_contact_fields_sort_value

Revision ID: a3f1c9d2e4b6
Revises: 30ae0fd93125

"""

import sqlalchemy as sa
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

    # Backfill in id-ordered batches so memory stays bounded on large tables.
    # unidecode is only available in Python, so the value is normalized row by
    # row rather than in SQL.
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
        sort_values = [
            {"b_id": contact_id, "b_sort_value": unidecode(value)}
            for contact_id, value in rows
        ]
        conn.execute(
            _contact_fields.update()
            .where(_contact_fields.c.id == sa.bindparam("b_id"))
            .values(sort_value=sa.bindparam("b_sort_value")),
            sort_values,
        )
        last_id = rows[-1][0]


def downgrade() -> None:
    op.drop_column(TABLE_NAME, COLUMN_NAME)
