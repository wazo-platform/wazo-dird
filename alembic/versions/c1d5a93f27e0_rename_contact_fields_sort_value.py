"""rename_contact_fields_sort_value_to_normalized_value

Revision ID: c1d5a93f27e0
Revises: a3f1c9d2e4b6

"""

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = 'c1d5a93f27e0'
down_revision = 'a3f1c9d2e4b6'

TABLE_NAME = 'dird_contact_fields'
OLD_NAME = 'sort_value'
NEW_NAME = 'normalized_value'


def upgrade() -> None:
    op.alter_column(TABLE_NAME, OLD_NAME, new_column_name=NEW_NAME)


def downgrade() -> None:
    op.alter_column(TABLE_NAME, NEW_NAME, new_column_name=OLD_NAME)
