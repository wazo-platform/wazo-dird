"""squashed baseline wazo-25.14

Revision ID: 2adc8aff56ea
Revises: None

"""

import os

# alembic exposes op as a runtime proxy that mypy cannot see statically
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision = '2adc8aff56ea'
down_revision = None


def upgrade() -> None:
    # Read and execute the SQL dump file
    versions_dir_path = os.path.dirname(__file__)
    sql_file_path = os.path.join(versions_dir_path, 'baseline-2514.sql')

    with open(sql_file_path) as f:
        sql_content = f.read()

    # Execute the SQL content
    op.execute(sql_content)


def downgrade() -> None:
    pass
