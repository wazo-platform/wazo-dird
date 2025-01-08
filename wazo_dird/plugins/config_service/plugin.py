# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import threading

from wazo_bus.resources.auth.events import TenantCreatedEvent
from wazo_bus.resources.localization.event import LocalizationEditedEvent

from wazo_dird import BaseServicePlugin, database
from wazo_dird.database.helpers import Session
from wazo_dird.database.queries.tenant import TenantCRUD

logger = logging.getLogger(__name__)


DEFAULT_DISPLAY_COLUMNS = [
    {'field': 'name', 'title': 'Nom', 'type': 'name'},
    {'field': 'firstname', 'title': 'Prénom', 'type': 'firstname'},
    {'field': 'lastname', 'title': 'Nom de famille', 'type': 'lastname'},
    {
        'field': 'phone',
        'title': "Num\xE9ro",
        'type': 'number',
        'number_display': '{name}',
    },
    {
        'field': 'phone_mobile',
        'title': 'Mobile',
        'type': 'number',
        'number_display': '{name} (mobile)',
    },
    {'field': 'voicemail', 'title': "Bo\xEEte vocale", 'type': 'voicemail'},
    {'field': 'favorite', 'title': 'Favoris', 'type': 'favorite'},
    {'field': 'email', 'title': 'E-mail', 'type': 'email'},
]
CONFERENCE_SOURCE_BODY = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-dird-conference-backend-key.yml',
        'version': '0.1',
    },
    'confd': {
        'host': 'localhost',
        'port': 9486,
        'prefix': None,
        'https': False,
        'version': '1.1',
    },
    'format_columns': {'phone': '{extensions[0]}', 'reverse': '{name}'},
    'searched_columns': ['name', 'extensions', 'incalls'],
    'first_matched_columns': ['extensions', 'incalls'],
}
PERSONAL_SOURCE_BODY = {
    'name': 'personal',
    'format_columns': {
        'phone': '{number}',
        'name': '{firstname} {lastname}',
        'phone_mobile': '{mobile}',
        'reverse': '{firstname} {lastname}',
    },
    'searched_columns': ['firstname', 'lastname', 'number', 'mobile', 'fax'],
    'first_matched_columns': ['number', 'mobile'],
}
WAZO_SOURCE_BODY = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml',
        'version': '0.1',
    },
    'confd': {
        'host': 'localhost',
        'port': 9486,
        'prefix': None,
        'https': False,
        'version': '1.1',
    },
    'format_columns': {
        'phone': '{exten}',
        'name': '{firstname} {lastname}',
        'reverse': '{firstname} {lastname}',
    },
    'searched_columns': ['firstname', 'lastname', 'full_name', 'exten'],
    'first_matched_columns': ['exten', 'mobile_phone_number'],
}
OFFICE_365_SOURCE_BODY = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml',
        'version': '0.1',
    },
    'endpoint': 'https://graph.microsoft.com/v1.0/me/contacts',
    'format_columns': {
        'name': '{givenName} {surname}',
        'phone_mobile': '{mobilePhone}',
        'reverse': '{givenName} {surname}',
        'phone': '{numbers_except_label[mobilePhone][0]}',
    },
    'searched_columns': [
        'givenName',
        'surname',
        'businessPhones',
        'homePhones',
        'mobilePhone',
    ],
    'first_matched_columns': ['businessPhones', 'mobilePhone', 'homePhones'],
}
GOOGLE_SOURCE_BODY = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml',
        'version': '0.1',
    },
    'format_columns': {
        'phone_mobile': '{numbers_by_label[mobile]}',
        'reverse': '{name}',
        'phone': '{numbers_except_label[mobile][0]}',
    },
    'searched_columns': ['name', 'numbers', 'familyName', 'givenName'],
    'first_matched_columns': ['numbers'],
}


class ConfigServicePlugin(BaseServicePlugin):
    def __init__(self):
        self._service = None

    def load(self, dependencies):
        bus = dependencies['bus']
        config = dependencies['config']
        controller = dependencies['controller']
        confd_client = dependencies['confd_client']
        return Service(
            config, bus, controller, database.TenantCRUD(Session), confd_client
        )


class Service:
    # Changing root logger log-level requires application-wide lock.
    # This lock will be shared across all instances.
    _lock = threading.Lock()

    def __init__(self, config, bus, controller, tenant_crud: TenantCRUD, confd_client):
        self._bus = bus
        self._config = config
        self._controller = controller
        self._tenant_crud = tenant_crud
        self._confd_client = confd_client

        self._bus.subscribe(TenantCreatedEvent.name, self._on_new_tenant_event)
        self._bus.subscribe(
            LocalizationEditedEvent.name, self._on_localization_edited_event
        )

    def get_config(self):
        return self._config

    def update_config(self, config: dict) -> None:
        with self._lock:
            self._update_debug(config['debug'])
            self._config['debug'] = config['debug']

    def _update_debug(self, debug: bool) -> None:
        if debug:
            self._enable_debug()
        else:
            self._disable_debug()

    def _enable_debug(self) -> None:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

    def _disable_debug(self) -> None:
        root_logger = logging.getLogger()
        root_logger.setLevel(self._config['log_level'])

    def _on_new_tenant_event(self, tenant):
        name = tenant['name']
        uuid = tenant['uuid']
        sources = self._auto_create_sources(uuid, name)
        display = self._auto_create_display(uuid, name)
        self._auto_create_profile(uuid, name, display, sources)

    def _on_localization_edited_event(self, localization):
        tenant_uuid = localization['tenant_uuid']
        country = localization['country']

        self._tenant_crud.create_or_edit(tenant_uuid, {'country': country})

    def _add_source(self, backend, body):
        source_service = self._controller.services.get('source')
        try:
            source = source_service.create(backend, **body)
            logger.info('auto created %s source %s', backend, body)
            return source
        except Exception as e:
            logger.info('failed to create %s source %s', backend, e)

    def _add_conference_source(self, tenant_uuid, name):
        backend = 'conference'
        body = dict(CONFERENCE_SOURCE_BODY)
        body['name'] = f'auto_{backend}_{name}'
        body['tenant_uuid'] = tenant_uuid
        return self._add_source(backend, body)

    def _add_personal_source(self, tenant_uuid, name):
        backend = 'personal'
        body = dict(PERSONAL_SOURCE_BODY)
        body['tenant_uuid'] = tenant_uuid
        return self._add_source(backend, body)

    def _add_wazo_user_source(self, tenant_uuid, name):
        backend = 'wazo'
        body = dict(WAZO_SOURCE_BODY)
        body['name'] = f'auto_{backend}_{name}'
        body['tenant_uuid'] = tenant_uuid
        return self._add_source(backend, body)

    def _add_office365_source(self, tenant_uuid, name):
        backend = 'office365'
        body = dict(OFFICE_365_SOURCE_BODY)
        body['name'] = f'auto_{backend}_{name}'
        body['tenant_uuid'] = tenant_uuid
        return self._add_source(backend, body)

    def _add_google_source(self, tenant_uuid, name):
        backend = 'google'
        body = dict(GOOGLE_SOURCE_BODY)
        body['name'] = f'auto_{backend}_{name}'
        body['tenant_uuid'] = tenant_uuid
        return self._add_source(backend, body)

    def _auto_create_sources(self, tenant_uuid, name):
        logger.info('creating sources for tenant "%s"', name)
        sources = [
            self._add_conference_source(tenant_uuid, name),
            self._add_personal_source(tenant_uuid, name),
            self._add_wazo_user_source(tenant_uuid, name),
            self._add_office365_source(tenant_uuid, name),
            self._add_google_source(tenant_uuid, name),
        ]
        return [s for s in sources if s is not None]

    def _auto_create_display(self, tenant_uuid, name):
        display_service = self._controller.services.get('display')
        try:
            display = display_service.create(
                tenant_uuid=tenant_uuid,
                name=f'auto_{name}',
                columns=DEFAULT_DISPLAY_COLUMNS,
            )
            logger.info(
                'display %s auto created for tenant %s',
                display['uuid'],
                display['tenant_uuid'],
            )
            return display
        except Exception as e:
            logger.info('auto display creation failed %s', e)

    def _auto_create_profile(self, tenant_uuid, name, display, sources):
        logger.info('creating a new profile for tenant "%s"', name)
        body = {
            'name': 'default',
            'tenant_uuid': tenant_uuid,
            'display': display,
            'services': {
                'lookup': {'sources': sources},
                'favorites': {'sources': sources},
                'reverse': {'sources': sources, 'timeout': 0.5},
            },
        }

        profile_service = self._controller.services.get('profile')
        try:
            profile = profile_service.create(**body)
            logger.info('auto created profile %s', profile)
        except Exception as e:
            logger.info('auto profile creation failes %s', e)

    def _sync_tenants(self):
        tenants = self._confd_client.tenants.list(recurse=True)['items']

        for tenant in tenants:
            try:
                localization = self._confd_client.localization.get(
                    tenant_uuid=tenant['uuid']
                )
            except Exception:
                continue
            else:
                self._tenant_crud.create_or_edit(
                    tenant['uuid'], {'country': localization['country']}
                )
