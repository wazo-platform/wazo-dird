# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, contains, contains_inanyorder, has_entries, has_item
from wazo_test_helpers import until
from wazo_test_helpers.auth import AuthClient as MockAuthClient
from wazo_test_helpers.auth import MockUserToken
from wazo_test_helpers.bus import BusClient
from wazo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import SUB_TENANT
from .helpers.wait_strategy import RestApiOkWaitStrategy


class TestConfigAutoCreation(BaseDirdIntegrationTest):
    asset = 'all_routes'
    wait_strategy = RestApiOkWaitStrategy()

    def setUp(self):
        super().setUp()
        self.tenant_uuid = SUB_TENANT
        self.tenant_name = 'mytenant'
        bus_port = self.service_port(5672, 'rabbitmq')
        self.bus = BusClient.from_connection_fields(
            host='127.0.0.1',
            port=bus_port,
            exchange_name='wazo-headers',
            exchange_type='headers',
        )

        self.mock_auth_client = MockAuthClient(
            '127.0.0.1', self.service_port(9497, 'auth')
        )

        def wait_for_dird_bus_connection():
            response = self.client.status.get()
            assert_that(response, has_entries(bus_consumer={'status': 'ok'}))

        until.assert_(wait_for_dird_bus_connection, timeout=6)

    def test_conference_source(self):
        self._publish_tenant_created_event()

        def check():
            response = self.client.conference_source.list(tenant_uuid=self.tenant_uuid)
            key_file = '/var/lib/wazo-auth-keys/wazo-dird-conference-backend-key.yml'
            assert_that(
                response,
                has_entries(
                    items=has_item(
                        has_entries(
                            uuid=uuid_(),
                            tenant_uuid=self.tenant_uuid,
                            name='auto_conference_mytenant',
                            auth={
                                'host': 'localhost',
                                'port': 9497,
                                'prefix': None,
                                'https': False,
                                'version': '0.1',
                                'key_file': key_file,
                            },
                            confd={
                                'host': 'localhost',
                                'port': 9486,
                                'prefix': None,
                                'https': False,
                                'version': '1.1',
                            },
                            first_matched_columns=contains_inanyorder(
                                'extensions', 'incalls'
                            ),
                            searched_columns=contains_inanyorder(
                                'name', 'extensions', 'incalls'
                            ),
                            format_columns={
                                'phone': '{extensions[0]}',
                                'reverse': '{name}',
                            },
                        )
                    )
                ),
            )

        until.assert_(check, timeout=3)
        for source in self.client.conference_source.list(tenant_uuid=self.tenant_uuid)[
            'items'
        ]:
            if source['name'] == 'auto_conference_mytenant':
                conference_uuid = source['uuid']

        def check():
            response = self.client.profiles.list(
                name='default', tenant_uuid=self.tenant_uuid
            )
            assert_that(
                response,
                has_entries(
                    items=has_item(
                        has_entries(
                            services=has_entries(
                                lookup=has_entries(
                                    sources=has_item(has_entries(uuid=conference_uuid))
                                )
                            )
                        )
                    )
                ),
            )

        until.assert_(check, timeout=3)

    def test_google_source(self):
        self._publish_tenant_created_event()

        def check():
            response = self.client.backends.list_sources(
                'google', tenant_uuid=self.tenant_uuid
            )
            assert_that(
                response,
                has_entries(
                    items=has_item(
                        has_entries(
                            uuid=uuid_(),
                            tenant_uuid=self.tenant_uuid,
                            name='auto_google_mytenant',
                            auth={
                                'host': 'localhost',
                                'port': 9497,
                                'prefix': None,
                                'https': False,
                                'version': '0.1',
                            },
                            first_matched_columns=has_item('numbers'),
                            searched_columns=contains_inanyorder(
                                'name', 'numbers', 'familyName', 'givenName'
                            ),
                            format_columns=has_entries(
                                phone_mobile='{numbers_by_label[mobile]}',
                                reverse='{name}',
                                phone='{numbers_except_label[mobile][0]}',
                            ),
                        )
                    )
                ),
            )

        until.assert_(check, timeout=3)
        for source in self.client.backends.list_sources(
            'google', tenant_uuid=self.tenant_uuid
        )['items']:
            if source['name'] == 'auto_google_mytenant':
                google_source_uuid = source['uuid']

        def check():
            response = self.client.profiles.list(
                name='default', tenant_uuid=self.tenant_uuid
            )
            assert_that(
                response,
                has_entries(
                    items=has_item(
                        has_entries(
                            services=has_entries(
                                lookup=has_entries(
                                    sources=has_item(
                                        has_entries(uuid=google_source_uuid)
                                    )
                                )
                            )
                        )
                    )
                ),
            )

        until.assert_(check, timeout=3)

    def test_lookup(self):
        self._publish_tenant_created_event()
        token = self._create_user()

        def check():
            result = self.lookup('alice', 'default', token=token)
            assert_that(
                result,
                has_entries(
                    column_headers=contains(
                        'Nom', 'Numéro', 'Mobile', 'Boîte vocale', 'Favoris', 'E-mail'
                    ),
                    column_types=contains(
                        'name', 'number', 'number', 'voicemail', 'favorite', 'email'
                    ),
                    results=contains_inanyorder(
                        has_entries(
                            column_values=contains(
                                'Alice', '1234', None, None, False, None
                            )
                        )
                    ),
                ),
            )

        with self.personal({'firstname': 'Alice', 'number': '1234'}, token=token):
            until.assert_(check, timeout=3)

    def _create_user(self):
        self.mock_auth_client.set_tenants(
            {
                'total': 1,
                'filtered': 1,
                'items': [{'uuid': self.tenant_uuid, 'name': self.tenant_name}],
            }
        )
        token = MockUserToken.some_token(metadata={'tenant_uuid': self.tenant_uuid})
        self.mock_auth_client.set_token(token)
        return token.token_id

    def _publish_tenant_created_event(self):
        payload = {'data': {'uuid': self.tenant_uuid, 'name': self.tenant_name}}
        self.bus.publish(
            payload,
            headers={
                'name': 'auth_tenant_added',
                'tenant_uuid': self.tenant_uuid,
                'origin_uuid': 'the-wazo-uuid',
            },
        )
