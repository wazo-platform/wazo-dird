"""add indices for foreign keys

Revision ID: 9c426a2c7e59
Revises: 4f76dc8ffb57

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '9c426a2c7e59'
down_revision = '4f76dc8ffb57'


def upgrade():
    op.create_index(
        'dird_contact__idx__user_uuid',
        'dird_contact',
        ['user_uuid'],
    )
    op.create_index(
        'dird_contact__idx__phonebook_id',
        'dird_contact',
        ['phonebook_id'],
    )
    op.create_index(
        'dird_contact_fields__idx__contact_uuid',
        'dird_contact_fields',
        ['contact_uuid'],
    )
    op.create_index(
        'dird_display__idx__tenant_uuid',
        'dird_display',
        ['tenant_uuid'],
    )
    op.create_index(
        'dird_display_column__idx__display_uuid',
        'dird_display_column',
        ['display_uuid'],
    )
    op.create_index(
        'dird_phonebook__idx__tenant_uuid',
        'dird_phonebook',
        ['tenant_uuid'],
    )
    op.create_index(
        'dird_profile__idx__tenant_uuid',
        'dird_profile',
        ['tenant_uuid'],
    )
    op.create_index(
        'dird_profile__idx__display_tenant_uuid',
        'dird_profile',
        ['display_tenant_uuid'],
    )
    op.create_index(
        'dird_profile__idx__display_uuid',
        'dird_profile',
        ['display_uuid'],
    )
    op.create_index(
        'dird_profile_service__idx__profile_uuid',
        'dird_profile_service',
        ['profile_uuid'],
    )
    op.create_index(
        'dird_profile_service__idx__profile_tenant_uuid',
        'dird_profile_service',
        ['profile_tenant_uuid'],
    )
    op.create_index(
        'dird_profile_service__idx__service_uuid',
        'dird_profile_service',
        ['service_uuid'],
    )
    op.create_index(
        'dird_source__idx__tenant_uuid',
        'dird_source',
        ['tenant_uuid'],
    )


def downgrade():
    op.drop_index('dird_source__idx__tenant_uuid')
    op.drop_index('dird_profile_service__idx__service_uuid')
    op.drop_index('dird_profile_service__idx__profile_tenant_uuid')
    op.drop_index('dird_profile_service__idx__profile_uuid')
    op.drop_index('dird_profile__idx__display_uuid')
    op.drop_index('dird_profile__idx__display_tenant_uuid')
    op.drop_index('dird_profile__idx__tenant_uuid')
    op.drop_index('dird_phonebook__idx__tenant_uuid')
    op.drop_index('dird_display_column__idx__display_uuid')
    op.drop_index('dird_display__idx__tenant_uuid')
    op.drop_index('dird_contact_fields__idx__contact_uuid')
    op.drop_index('dird_contact__idx__phonebook_id')
    op.drop_index('dird_contact__idx__user_uuid')
