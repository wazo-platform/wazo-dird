"""remove duplicate contact_field id

Revision ID: 1e0397088fa7
Revises: 1e66a71e0352

"""

# revision identifiers, used by Alembic.
revision = '1e0397088fa7'
down_revision = '1e66a71e0352'

import sqlalchemy as sa
from alembic import op
from sqlalchemy import sql

contact_field_table = sql.table('dird_contact_fields',
                                sql.column('id'),
                                sql.column('name'),
                                sql.column('value'),
                                sql.column('contact_uuid'))


def upgrade():
    purge_divergent_id_contact_fields()
    known_contact_ids = set()
    for id_contact_field_row in get_id_contact_field_rows():
        if id_contact_field_row.contact_uuid not in known_contact_ids:
            known_contact_ids.add(id_contact_field_row.contact_uuid)
        else:
            query = contact_field_table.delete().where(contact_field_table.c.id == id_contact_field_row.id)
            op.get_bind().execute(query)


def purge_divergent_id_contact_fields():
    query = contact_field_table.delete().where(sql.and_(contact_field_table.c.name == 'id',
                                                        contact_field_table.c.value != contact_field_table.c.contact_uuid))
    op.get_bind().execute(query)


def get_id_contact_field_rows():
    id_contact_fields = (sql.select([contact_field_table.c.id, contact_field_table.c.contact_uuid])
                         .where(sql.and_(contact_field_table.c.name == 'id',
                                         contact_field_table.c.value == contact_field_table.c.contact_uuid)))
    return op.get_bind().execute(id_contact_fields)


def downgrade():
    pass
