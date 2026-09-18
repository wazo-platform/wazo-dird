"""add_contact_fields_normalized_value_trgm_index

Revision ID: d4b8f0c61e57
Revises: c1d5a93f27e0

"""

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'd4b8f0c61e57'
down_revision = 'c1d5a93f27e0'

INDEX_NAME = 'dird_contact_fields__idx__normalized_value_trgm'
TABLE_NAME = 'dird_contact_fields'
COLUMN_NAME = 'normalized_value'


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        [COLUMN_NAME],
        postgresql_using='gin',
        postgresql_ops={COLUMN_NAME: 'gin_trgm_ops'},
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
