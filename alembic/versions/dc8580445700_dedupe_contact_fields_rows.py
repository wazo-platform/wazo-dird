"""dedupe_contact_fields_rows

Revision ID: dc8580445700
Revises: 4f2c91ab07de

"""

import sqlalchemy as sa

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'dc8580445700'
down_revision = '4f2c91ab07de'

_contact_fields = sa.table(
    'dird_contact_fields',
    sa.column('id', sa.Integer),
    sa.column('name', sa.Text),
    sa.column('contact_uuid', sa.String),
)


def upgrade() -> None:
    other = _contact_fields.alias('other')
    keep_id = (
        sa.select(sa.func.min(other.c.id))
        .where(
            other.c.contact_uuid == _contact_fields.c.contact_uuid,
            other.c.name == _contact_fields.c.name,
        )
        .scalar_subquery()
    )
    op.get_bind().execute(
        _contact_fields.delete().where(
            _contact_fields.c.id > keep_id,
        )
    )


def downgrade() -> None:
    pass
