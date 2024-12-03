"""add firstname and lastname to display

Revision ID: 042a2ba167c0
Revises: 7c49d771407a

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '042a2ba167c0'
down_revision = '7c49d771407a'

display_tbl = sa.table(
    'dird_display',
    sa.column('uuid'),
    sa.column('name'),
)
display_column_tbl = sa.table(
    'dird_display_column',
    sa.column('display_uuid'),
    sa.column('field'),
    sa.column('title'),
    sa.column('type'),
)


def add_display_column(display_uuid, field, title):
    type_ = field
    op.execute(
        display_column_tbl.insert().values(
            display_uuid=display_uuid,
            field=field,
            title=title,
            type=type_,
        )
    )


def list_default_displays():
    query = sa.sql.select([display_tbl.c.uuid]).where(
        display_tbl.c.name.startswith('auto_'),
    )
    return {row.uuid for row in op.get_bind().execute(query)}


def list_display_uuid_by_field(field_name):
    query = sa.sql.select([display_column_tbl.c.display_uuid]).where(
        display_column_tbl.c.field == field_name,
    )
    return {row.display_uuid for row in op.get_bind().execute(query)}


def list_displays_with_firstname():
    return list_display_uuid_by_field('firstname')


def list_displays_with_lastname():
    return list_display_uuid_by_field('lastname')


def upgrade():
    default_display_uuids = list_default_displays()
    displays_with_firstname = list_displays_with_firstname()
    displays_with_lastname = list_displays_with_lastname()
    displays_requiring_firstname = default_display_uuids - displays_with_firstname
    displays_requiring_lastname = default_display_uuids - displays_with_lastname
    for display_uuid in displays_requiring_firstname:
        add_display_column(display_uuid, 'firstname', 'Prénom')
    for display_uuid in displays_requiring_lastname:
        add_display_column(display_uuid, 'lastname', 'Nom de famille')


def downgrade():
    pass
