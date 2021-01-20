"""add-missing-fk-cascade

Revision ID: 4f76dc8ffb57
Revises: 29d00094fd68

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '4f76dc8ffb57'
down_revision = '29d00094fd68'


def upgrade():
    op.drop_constraint(
        'dird_contact_user_uuid_fkey', 'dird_contact', type_='foreignkey'
    )
    op.drop_constraint(
        'dird_favorite_user_uuid_fkey', 'dird_favorite', type_='foreignkey'
    )
    op.create_foreign_key(
        'dird_contact_user_uuid_fkey',
        'dird_contact',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'dird_favorite_user_uuid_fkey',
        'dird_favorite',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
        ondelete='CASCADE',
    )


def downgrade():
    op.drop_constraint(
        'dird_contact_user_uuid_fkey', 'dird_contact', type_='foreignkey'
    )
    op.drop_constraint(
        'dird_favorite_user_uuid_fkey', 'dird_favorite', type_='foreignkey'
    )
    op.create_foreign_key(
        'dird_contact_user_uuid_fkey',
        'dird_contact',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
    )
    op.create_foreign_key(
        'dird_favorite_user_uuid_fkey',
        'dird_favorite',
        'dird_user',
        ['user_uuid'],
        ['user_uuid'],
    )
