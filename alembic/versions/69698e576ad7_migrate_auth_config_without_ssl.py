"""migrate_auth_config_without_ssl

Revision ID: 69698e576ad7
Revises: 3966fb49ce71

"""

import json

from sqlalchemy import sql

from alembic import op

# revision identifiers, used by Alembic.
revision = '69698e576ad7'
down_revision = '3966fb49ce71'

dird_source_table = sql.table(
    'dird_source',
    sql.column('uuid'),
    sql.column('extra_fields'),
    sql.column('backend'),
)


def upgrade():
    dird_sources = get_sources()
    for source in dird_sources:
        auth_config = source.extra_fields.get('auth')
        if not auth_config:
            continue

        if (
            auth_config['host'] in ('localhost', '127.0.0.1')
            and auth_config['port'] == 9497
        ):
            source.extra_fields['auth']['prefix'] = None
            source.extra_fields['auth']['https'] = False
            source.extra_fields['auth']['verify_certificate'] = True
        else:
            source.extra_fields['auth']['prefix'] = '/api/auth'
            source.extra_fields['auth']['https'] = True
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
    ).where(
        dird_source_table.c.backend.in_(['wazo', 'conference', 'office365', 'google'])
    )
    return op.get_bind().execute(sources)


def downgrade():
    dird_sources = get_sources()
    for source in dird_sources:
        auth_config = source.extra_fields.get('auth')
        if not auth_config:
            continue

        source.extra_fields['auth'].pop('prefix', None)
        source.extra_fields['auth'].pop('https', None)
        if (
            auth_config['host'] in ('localhost', '127.0.0.1')
            and auth_config['port'] == 9497
        ):
            source.extra_fields['auth'][
                'verify_certificate'
            ] = '/usr/share/xivo-certs/server.crt'
        query = (
            dird_source_table.update()
            .where(dird_source_table.c.uuid == source.uuid)
            .values(extra_fields=json.dumps(source.extra_fields))
        )
        op.get_bind().execute(query)
