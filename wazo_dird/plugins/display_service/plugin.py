# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import kombu

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.auth.events import TenantCreatedEvent

from wazo_dird import (
    BaseServicePlugin,
    database,
)

logger = logging.getLogger(__name__)


class DisplayServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        config = dependencies['config']
        bus = dependencies['bus']
        db_uri = config['db_uri']
        Session = self._new_db_session(db_uri)
        return _DisplayService(database.DisplayCRUD(Session), bus)

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _DisplayService:

    QUEUE = kombu.Queue(
        exchange=kombu.Exchange('xivo', type='topic'),
        routing_key='auth.tenants.*.created',
        exclusive=True,
    )
    _default_display_columns = [
        {'field': 'name', 'title': 'Nom', 'type': 'name'},
        {'field': 'phone', 'title': "Num\xE9ro", 'type': 'number', 'number_display': '{name}'},
        {'field': 'phone_mobile', 'title': 'Mobile', 'type': 'number', 'number_display': '{name} (mobile)'},
        {'field': 'voicemail', 'title': "Bo\xEEte vocale", 'type': 'voicemail'},
        {'field': 'favorite', 'title': 'Favoris', 'type': 'favorite'},
        {'field': 'email', 'title': 'E-mail', 'type': 'email'},
    ]

    def __init__(self, crud, bus):
        self._display_crud = crud
        bus.add_consumer(self.QUEUE, self._on_new_tenant)

    def create(self, **body):
        return self._display_crud.create(**body)

    def list_(self, visible_tenants, **list_params):
        return self._display_crud.list_(visible_tenants, **list_params)

    def _auto_create_display(self, tenant_uuid, name):
        try:
            display = self.create(
                tenant_uuid=tenant_uuid,
                name='auto_{}'.format(name),
                columns=self._default_display_columns,
            )
            logger.info(
                'display %s auto created for tenant %s',
                display['uuid'], display['tenant_uuid'],
            )
        except Exception as e:
            logger.info('auto display creation failed %s', e)

    def _on_new_tenant(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, TenantCreatedEvent)
            body = event.marshal()
        except (InvalidMessage, KeyError):
            logger.info('Ignoring the following malformed bus message: %s', body)
        else:
            self._auto_create_display(body['uuid'], body['name'])
        finally:
            message.ack()
