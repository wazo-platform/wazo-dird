# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest.mock import Mock

from hamcrest import assert_that, contains, contains_inanyorder, empty, has_entries

from .helpers.base import BaseDirdIntegrationTest, DirdAssetRunningTestCase
from .helpers.config import new_conference_config
from .helpers.constants import MAIN_TENANT
from .helpers.utils import BackendWrapper


class TestConferencePlugin(DirdAssetRunningTestCase):
    asset = 'wazo_confd'

    def setUp(self):
        super().setUp()
        config = {
            'uuid': '9c2894cd-5bbb-479d-99f8-b0a361986984',
            'type': 'conference',
            'tenant_uuid': MAIN_TENANT,
            'name': 'local conferences',
            'searched_columns': ['name', 'extensions', 'incalls'],
            'first_matched_columns': ['extensions', 'incalls'],
            'auth': {
                'host': '127.0.0.1',
                'port': self.service_port(9497, 'auth'),
                'prefix': None,
                'https': False,
            },
            'confd': {
                'host': '127.0.0.1',
                'port': self.service_port(9486, 'confd'),
                'prefix': None,
                'https': False,
                'version': '1.1',
            },
            'format_columns': {
                'displayname': '{name}',
                'phone': '{extensions[0]}',
                'reverse': '{name}',
            },
        }
        dependencies = {'api': Mock(), 'config': config}
        self.backend = BackendWrapper('conference', dependencies)

    def tearDown(self):
        self.backend.unload()
        super().tearDown()

    def test_lookup_with_accent(self):
        result = self.backend.search('accent')
        assert_that(result, contains(has_entries(displayname='accént')))

    def test_lookup_by_name(self):
        result = self.backend.search('daily')
        assert_that(
            result,
            contains(
                has_entries(
                    displayname='daily scrum',
                    extensions=contains('4002'),
                    id=4,
                    incalls=empty(),
                    name='daily scrum',
                    phone='4002',
                    reverse='daily scrum',
                )
            ),
        )

    def test_lookup_by_extension(self):
        result = self.backend.search('4002')
        assert_that(
            result,
            contains(
                has_entries(
                    displayname='daily scrum',
                    extensions=contains('4002'),
                    id=4,
                    incalls=empty(),
                    name='daily scrum',
                    phone='4002',
                    reverse='daily scrum',
                )
            ),
        )

    def test_lookup_by_incall(self):
        result = self.backend.search('1009')
        assert_that(
            result,
            contains(
                has_entries(
                    displayname='test',
                    extensions=contains('4001'),
                    id=1,
                    incalls=contains('1009'),
                    name='test',
                    phone='4001',
                    reverse='test',
                )
            ),
        )

    def test_reverse_lookup_on_exten(self):
        result = self.backend.first('4002')
        assert_that(
            result,
            has_entries(
                displayname='daily scrum',
                extensions=contains('4002'),
                id=4,
                incalls=empty(),
                name='daily scrum',
                phone='4002',
                reverse='daily scrum',
            ),
        )

    def test_reverse_lookup_on_incall(self):
        result = self.backend.first('1009')
        assert_that(
            result,
            has_entries(
                displayname='test',
                extensions=contains('4001'),
                id=1,
                incalls=contains('1009'),
                name='test',
                phone='4001',
                reverse='test',
            ),
        )

    def test_match_all_returns_the_expected_result(self):
        result = self.backend.match_all(['4002', '1009'])

        assert_that(
            result,
            contains_inanyorder(
                has_entries(displayname='test'),
                has_entries(displayname='daily scrum'),
            ),
        )

    def test_favorites(self):
        result = self.backend.list(['1', '4'], None)
        assert_that(
            result,
            contains_inanyorder(
                has_entries(id=4, displayname='daily scrum'),
                has_entries(id=1, displayname='test'),
            ),
        )


class TestNoConfd(BaseDirdIntegrationTest):
    asset = 'wazo_no_confd'
    config_factory = new_conference_config

    def test_given_no_confd_when_lookup_then_returns_no_results(self):
        result = self.lookup('daily', 'default')
        assert_that(result['results'], contains())
