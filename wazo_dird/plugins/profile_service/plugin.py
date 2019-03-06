# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import kombu

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.context.event import CreateContextEvent

from wazo_dird import exception

from wazo_dird import (
    BaseServicePlugin,
    database,
)

logger = logging.getLogger(__name__)


class ProfileServicePlugin(BaseServicePlugin):

    def load(self, dependencies):
        config = dependencies['config']
        bus = dependencies['bus']
        controller = dependencies['controller']
        db_uri = config['db_uri']
        Session = self._new_db_session(db_uri)
        return _ProfileService(database.ProfileCRUD(Session), bus, controller)

    def _new_db_session(self, db_uri):
        self._Session = scoped_session(sessionmaker())
        engine = create_engine(db_uri)
        self._Session.configure(bind=engine)
        return self._Session


class _ProfileService:

    _QUEUE = kombu.Queue(
        exchange=kombu.Exchange('xivo', type='topic'),
        routing_key='config.contexts.created',
        exclusive=True,
    )

    def __init__(self, crud, bus, controller):
        self._profile_crud = crud
        self._controller = controller
        bus.add_consumer(self._QUEUE, self._on_new_context)

    def create(self, **body):
        return self._profile_crud.create(body)

    def get_by_name(self, tenant_uuid, name):
        for profile in self._profile_crud.list_([tenant_uuid], name=name):
            return profile

        raise exception.NoSuchProfile(name)

    def list_(self, visible_tenants, **list_params):
        return self._profile_crud.list_(visible_tenants, **list_params)

    def _auto_create_profile(self, tenant_uuid, name):
        logger.info('creating a new profile for context "%s"', name)
        sources = self._find_auto_generated_sources(tenant_uuid)
        display = self._find_auto_generated_display(tenant_uuid)
        body = {
            'name': name,
            'tenant_uuid': tenant_uuid,
            'display': display,
            'services': {
                'lookup': {'sources': sources},
                'favorites': {'sources': sources},
                'reverse': {
                    'sources': sources,
                    'timeout': 0.5,
                },
            },
        }

        try:
            self.create(**body)
        except Exception as e:
            logger.info('auto profile creation failes %s', e)

    def _find_auto_generated_sources(self, tenant_uuid):
        source_service = self._controller.services.get('source')
        if not source_service:
            logger.info('no source service configured')
            return []

        available_sources = source_service.list_(None, [tenant_uuid])
        auto_generated_source_backends = ['wazo', 'personal', 'office365']

        result = []
        for source in available_sources:
            if source['backend'] not in auto_generated_source_backends:
                continue
            if not source['name'].startswith('auto_'):
                continue
            result.append(source)
        return result

    def _find_auto_generated_display(self, tenant_uuid):
        display_service = self._controller.services.get('display')
        if not display_service:
            logger.info('no display service configured')
            return None

        available_displays = display_service.list_([tenant_uuid])

        for display in available_displays:
            if not display['name'].startswith('auto_'):
                continue
            return display

    def _on_new_context(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, CreateContextEvent)
            body = event.marshal()
        except (InvalidMessage, KeyError):
            logger.info('Ignoring the following malformed bus message: %s', body)
        else:
            if body['type'] != 'internal':
                return
            self._auto_create_profile(body['tenant_uuid'], body['name'])
        finally:
            message.ack()
