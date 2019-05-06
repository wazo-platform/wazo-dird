# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains,
    has_entries,
)
from mock import Mock

from .base_dird_integration_test import BackendWrapper
from .helpers.base import DirdAssetRunningTestCase
from .helpers.constants import MAIN_TENANT


class TestConferencePlugin(DirdAssetRunningTestCase):

    asset = 'wazo_users'

    def setUp(self):
        super().setUp()
        config = {
            'uuid': '9c2894cd-5bbb-479d-99f8-b0a361986984',
            'type': 'conference',
            'tenant_uuid': MAIN_TENANT,
            'name': 'local conferences',
            'searched_columns': ['name', 'extensions', 'dids'],
            'first_matched_columns': ['extensions', 'dirds'],
            'auth': {
                'host': 'localhost',
                'port': self.service_port(9497, 'auth'),
                'verify_certificate': False,
            },
            'confd': {
                'host': 'localhost',
                'port': self.service_port(9486, 'confd'),
                'version': '1.1',
                'https': False,
            },
            'format_columns': {
                'displayname': '{name}',
                'phone': '{extensions[0]}',
                'reverse': '{name}',
            },
        }
        dependencies = {
            'api': Mock(),
            'config': config,
        }
        self.backend = BackendWrapper('conference', dependencies)

    def tearDown(self):
        self.backend.unload()
        super().tearDown()

    def test_lookup(self):
        result = self.backend.search('daily')

        assert_that(result, contains(
            has_entries(
            ),
        ))

        self.fail()
