"""add_unique_index_contact_fields_name_contact_uuid

Revision ID: 52869e467b80
Revises: dc8580445700

"""

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = '52869e467b80'
down_revision = 'dc8580445700'

INDEX_NAME = 'dird_contact_fields__idx__name_contact_uuid'
TABLE_NAME = 'dird_contact_fields'


def upgrade() -> None:
    op.create_index(INDEX_NAME, TABLE_NAME, ['name', 'contact_uuid'], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
