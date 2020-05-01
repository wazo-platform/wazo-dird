"""migrate_confd_config_without_ssl

Revision ID: 0542e068b5ef
Revises: 40298554e752

"""

import json

from alembic import op
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '0542e068b5ef'
down_revision = '40298554e752'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('extra_fields'),
    sql.column('backend'),
)


def upgrade():
    dird_sources = get_sources()
    for source in dird_sources:
        confd_config = source.extra_fields.get('confd')
        if not confd_config:
            continue

        if (
            confd_config['host'] in ('localhost', '127.0.0.1')
            and confd_config['port'] == 9486
        ):
            source.extra_fields['confd']['prefix'] = None
            source.extra_fields['confd']['https'] = False
            source.extra_fields['confd'].pop('verify_certificate', None)
        else:
            source.extra_fields['confd']['prefix'] = '/api/confd'
        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(extra_fields=json.dumps(source.extra_fields))
        )
        op.get_bind().execute(query)


def get_sources():
    sources = sql.select(
        [
            dird_source_table.c.uuid,
            dird_source_table.c.extra_fields,
            dird_source_table.c.backend,
        ]
    ).where(dird_source_table.c.backend.in_(['wazo', 'conference']))
    return op.get_bind().execute(sources)


def downgrade():
    dird_sources = get_sources()
    for source in dird_sources:
        confd_config = source.extra_fields.get('confd')
        if not confd_config:
            continue

        source.extra_fields['confd'].pop('prefix', None)
        if (
            confd_config['host'] in ('localhost', '127.0.0.1')
            and confd_config['port'] == 9486
        ):
            source.extra_fields['confd'][
                'verify_certificate'
            ] = '/usr/share/xivo-certs/server.crt'
        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(extra_fields=json.dumps(source.extra_fields))
        )
        op.get_bind().execute(query)
