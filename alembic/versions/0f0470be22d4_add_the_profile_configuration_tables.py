"""add the profile configuration tables

Revision ID: 0f0470be22d4
Revises: 5bfdd2178269

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '0f0470be22d4'
down_revision = '5bfdd2178269'


def upgrade():
    op.create_table(
        'dird_service',
        sa.Column(
            'uuid',
            sa.String(36),
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column(
            'name',
            sa.Text(),
            nullable=False,
            unique=True,
        )
    )

    op.create_table(
        'dird_profile',
        sa.Column(
            'uuid',
            sa.String(36),
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column(
            'tenant_uuid',
            sa.String(36),
            sa.ForeignKey('dird_tenant.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'name',
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            'display_uuid',
            sa.String(36),
            sa.ForeignKey('dird_display.uuid', ondelete='SET NULL'),
        )
    )

    op.create_table(
        'dird_profile_source',
        sa.Column(
            'profile_uuid',
            sa.String(36),
            sa.ForeignKey('dird_profile.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'source_uuid',
            sa.String(36),
            sa.ForeignKey('dird_source.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
    )

    op.create_table(
        'dird_profile_service',
        sa.Column(
            'profile_uuid',
            sa.String(36),
            sa.ForeignKey('dird_profile.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'service_uuid',
            sa.String(36),
            sa.ForeignKey('dird_source.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'config',
            JSON,
        ),
    )


def downgrade():
    op.drop_table('dird_profile_service')
    op.drop_table('dird_profile_source')
    op.drop_table('dird_profile')
    op.drop_table('dird_service')
