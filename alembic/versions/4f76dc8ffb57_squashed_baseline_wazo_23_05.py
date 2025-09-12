"""squashed baseline wazo-23.05

Revision ID: 4f76dc8ffb57
Revises: None

"""

import os

from alembic import op

# revision identifiers, used by Alembic.
revision = '4f76dc8ffb57'
down_revision = None


def upgrade():
    # Read and execute the SQL dump file
    versions_dir_path = os.path.dirname(__file__)
    sql_file_path = os.path.join(versions_dir_path, 'baseline-2305.sql')

    with open(sql_file_path) as f:
        sql_content = f.read()

    # Execute the SQL content
    op.execute(sql_content)


def downgrade():
    pass
