"""Add formatted number for contacts

Revision ID: 84952b3a05b7
Revises: 04c5c746a50b

"""

import sqlalchemy as sa
from sqlalchemy import sql
from xivo import reverse_lookup as rl

from alembic import op

# revision identifiers, used by Alembic.
revision = '84952b3a05b7'
down_revision = '04c5c746a50b'

contact_field_table = sql.table(
    'dird_contact_fields',
    sql.column('id'),
    sql.column('name'),
    sql.column('value'),
    sql.column('contact_uuid'),
)

tenant_table = sql.table(
    'tenant',
    sql.column('uuid'),
    sql.column('country'),
)

contact_table = sql.table(
    'dird_contact',
    sql.column('uuid'),
    sql.column('phonebook_uuid'),
    sql.column('user_uuid'),
)

phonebook_table = sql.table(
    'dird_phonebook',
    sql.column('uuid'),
    sql.column('tenant_uuid'),
)

user_table = sql.table(
    'chatd_user',
    sql.column('uuid'),
    sql.column('tenant_uuid'),
)


def get_tenants_country():
    tenants = sa.select([tenant_table.c.uuid, tenant_table.c.country])
    return {tenant.uuid: tenant.country for tenant in op.get_bind().execute(tenants)}


def get_contacts_tenant():
    phonebooks_tenant = (
        contact_field_table.join(
            contact_table,
            contact_field_table.c.contact_uuid == contact_table.c.uuid,
        )
        .join(
            phonebook_table,
            contact_table.c.phonebook_uuid == phonebook_table.c.uuid,
        )
        .select()
        .where(contact_field_table.c.name == 'number')
    )

    contacts_tenant = (
        contact_field_table.join(
            contact_table,
            contact_field_table.c.contact_uuid == contact_table.c.uuid,
        )
        .join(
            user_table,
            contact_table.c.user_uuid == sa.cast(user_table.c.uuid, sa.String),
        )
        .select()
        .where(contact_field_table.c.name == 'number')
    )

    from_phonebook = {
        contact.value: {
            'contact_uuid': contact.contact_uuid,
            'tenant_uuid': contact.tenant_uuid,
        }
        for contact in op.get_bind().execute(phonebooks_tenant)
    }
    from_contacts = {
        contact.value: {
            'contact_uuid': contact.contact_uuid,
            'tenant_uuid': contact.tenant_uuid,
        }
        for contact in op.get_bind().execute(contacts_tenant)
    }
    return from_phonebook | from_contacts


def upgrade():
    tenants = get_tenants_country()
    numbers = get_contacts_tenant()

    for number, row in numbers.items():
        formatted_number = rl.format_number(number, tenants[str(row['tenant_uuid'])])
        if not formatted_number or formatted_number == number:
            continue
        insert_formatted = sa.insert(contact_field_table).values(
            name='formatted_number',
            value=formatted_number,
            contact_uuid=sa.cast(row['contact_uuid'], sa.String),
        )
        _ = op.get_bind().execute(insert_formatted)


def downgrade():
    delete_formatted_numbers = contact_field_table.delete().where(
        contact_field_table.c.name == 'formatted_number'
    )
    _ = op.get_bind().execute(delete_formatted_numbers)
