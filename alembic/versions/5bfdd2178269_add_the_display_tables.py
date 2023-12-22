"""add the display tables

Revision ID: 5bfdd2178269
Revises: 0279b94ee7c6

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '5bfdd2178269'
down_revision = '0279b94ee7c6'


def upgrade():
    op.create_table(
        'dird_display',
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
        sa.Column('name', sa.Text(), nullable=False),
    )

    op.create_table(
        'dird_display_column',
        sa.Column(
            'uuid',
            sa.String(36),
            server_default=sa.text('uuid_generate_v4()'),
            primary_key=True,
        ),
        sa.Column(
            'display_uuid',
            sa.String(36),
            sa.ForeignKey('dird_display.uuid', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('field', sa.Text()),
        sa.Column('default', sa.Text()),
        sa.Column('type', sa.Text()),
        sa.Column('title', sa.Text()),
        sa.Column('number_display', sa.Text()),
    )


def downgrade():
    op.drop_table('dird_display_column')
    op.drop_table('dird_display')
