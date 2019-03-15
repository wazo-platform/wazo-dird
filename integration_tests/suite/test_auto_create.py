# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import kombu

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    has_entries,
)
from xivo_bus import (
    Publisher,
    Marshaler,
)
from xivo_bus.resources.auth.events import TenantCreatedEvent
from xivo_bus.resources.context.event import CreateContextEvent
from xivo_test_helpers import until
from xivo_test_helpers.bus import BusClient
from xivo_test_helpers.auth import (
    AuthClient as MockAuthClient,
    MockUserToken,
)

from .helpers.base import BaseDirdIntegrationTest


class TestConfigAutoCreation(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def setUp(self):
        self.tenant_uuid = '396f0350-028c-4eea-ac63-a80914631ab5'
        self.tenant_name = 'mytenant'
        self.context_name = 'here'
        bus_port = self.service_port(5672, 'rabbitmq')
        bus = BusClient.from_connection_fields(host='localhost', port=bus_port)
        until.true(bus.is_up, tries=5)

        bus_url = 'amqp://{username}:{password}@{host}:{port}//'.format(username='guest',
                                                                        password='guest',
                                                                        host='localhost',
                                                                        port=bus_port)
        connection = kombu.Connection(bus_url)
        connection.connect()
        marshaler = Marshaler('the-xivo-uuid')
        exchange = kombu.Exchange('xivo', type='topic')
        producer = kombu.Producer(connection, exchange=exchange, auto_declare=True)
        self.publisher = Publisher(producer, marshaler)
        self.mock_auth_client = MockAuthClient('localhost', self.service_port(9497, 'auth'))

    def test_lookup(self):
        # TODO add a /status and remove the sleep
        import time
        time.sleep(6)

        self._publish_tenant_created_event()
        self._publish_context_created_event()
        token = self._create_user()

        def check():
            result = self.lookup('alice', self.context_name, token=token)
            assert_that(result, has_entries(
                column_headers=contains(
                    'Nom',
                    'Numéro',
                    'Mobile',
                    'Boîte vocale',
                    'Favoris',
                    'E-mail',
                ),
                column_types=contains(
                    'name',
                    'number',
                    'number',
                    'voicemail',
                    'favorite',
                    'email',
                ),
                results=contains_inanyorder(has_entries(
                    column_values=contains(
                        'Alice',
                        '1234',
                        None,
                        None,
                        False,
                        None,
                    ),
                )),
            ))

        with self.personal({'firstname': 'Alice', 'number': '1234'}, token=token):
            until.assert_(check, tries=3)

    def _create_user(self):
        self.mock_auth_client.set_tenants({
            'total': 1,
            'filtered': 1,
            'items': [{'uuid': self.tenant_uuid, 'name': self.tenant_name}],
        })
        token = MockUserToken.some_token(metadata={'tenant_uuid': self.tenant_uuid})
        self.mock_auth_client.set_token(token)
        return token.token_id

    def _publish_tenant_created_event(self):
        msg = TenantCreatedEvent(uuid=self.tenant_uuid, name=self.tenant_name)
        self.publisher.publish(msg)

    def _publish_context_created_event(self):
        msg = CreateContextEvent(
            id=42,
            name=self.context_name,
            type='internal',
            tenant_uuid=self.tenant_uuid,
        )
        self.publisher.publish(msg)
