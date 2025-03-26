# Copyright 2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later


from hamcrest import assert_that, has_entries
from wazo_test_helpers import until
from wazo_test_helpers.bus import BusClient

from wazo_dird import database

from .helpers.base import BaseDirdIntegrationTest
from .helpers.utils import new_uuid

TENANT_UUID = new_uuid()


class TestTenantLocalizationEvent(BaseDirdIntegrationTest):
    asset = 'all_routes'

    def setUp(self):
        super().setUp()
        self._crud = database.TenantCRUD(self.Session)
        until.true(self.bus_is_up, tries=10)
        bus_port = self.service_port(5672, 'rabbitmq')
        self.bus = BusClient.from_connection_fields(
            host='127.0.0.1',
            port=bus_port,
            exchange_name='wazo-headers',
            exchange_type='headers',
        )

        def wait_for_dird_bus_connection():
            response = self.client.status.get()
            assert_that(response, has_entries(bus_consumer={'status': 'ok'}))

        until.assert_(wait_for_dird_bus_connection, timeout=6)

    def _publish_localization_event(self, tenant_uuid, country):
        payload = {'data': {'tenant_uuid': tenant_uuid, 'country': country}}
        header = {'name': 'localization_edited', 'tenant_uuid': tenant_uuid}
        self.bus.publish(payload, headers=header)

    def test_update_from_event(self):
        self._crud.create(tenant_uuid=TENANT_UUID, country='FR')
        self._publish_localization_event(TENANT_UUID, 'CA')

        def check():
            result = self._crud.get(TENANT_UUID)
            assert result == {'uuid': TENANT_UUID, 'country': 'CA'}

        until.assert_(check, timeout=5)
