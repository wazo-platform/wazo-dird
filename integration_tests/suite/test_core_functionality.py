# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import sh

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_TOKEN

from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_string
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_key


class TestCoreSourceManagement(BaseDirdIntegrationTest):

    asset = 'multiple_sources'

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        # second_csv does not search in column firstname
        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
            {'column_values': ['Alice', 'Alan', '1111'],
             'source': 'third_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': '1'}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class TestCoreSortLookup(BaseDirdIntegrationTest):

    asset = 'sort_lookup'

    def test_given_invalid_offset_then_lookup_return_404(self):
        result = self.get_lookup_result('A', 'default', token=VALID_TOKEN, offset=-1)
        assert_that(result.status_code, equal_to((404)))

    def test_given_invalid_limit_then_lookup_return_404(self):
        result = self.get_lookup_result('A', 'default', token=VALID_TOKEN, limit=-1)
        assert_that(result.status_code, equal_to((404)))

    def test_lookup_return_offset_when_has_more_results(self):
        result = self.lookup('A', 'default', limit=1, offset=1)

        assert_that(result['offset_next'], equal_to(2))
        assert_that(result['offset_previous'], equal_to(0))
        assert_that(result['links'], has_key('next'))
        assert_that(result['links'], has_key('previous'))
        assert_that(result['links']['next'], contains_string('limit=1&offset=2'))
        assert_that(result['links']['previous'], contains_string('limit=1&offset=0'))

    def test_lookup_not_return_offset_when_has_no_limit_results(self):
        result = self.lookup('A', 'default')

        assert_that(result['links'], is_not(has_key('next')))
        assert_that(result['links'], is_not(has_key('previous')))

    def test_lookup_return_results_sorted(self):
        result = self.lookup('A', 'default')

        expected_results = [
            {'column_values': ['AAA', 'BBB', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
            {'column_values': ['AAA', 'BBD', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
            {'column_values': ['BAA', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
        ]
        assert_that(result['results'], equal_to(expected_results))


class TestCoreSourceLoadingWithABrokenConfig(BaseDirdIntegrationTest):

    asset = 'broken_source_config'

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class TestBrokenDisplayConfig(BaseDirdIntegrationTest):

    asset = 'broken_display_config'

    def test_given_a_broken_display_config_when_headers_then_does_not_break_the_other_displays(self):
        result = self.headers('default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))

    def test_given_a_broken_display_config_when_lookup_then_does_not_break_the_other_displays(self):
        result = self.lookup('lice', 'default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number'))


class TestCoreSourceLoadingWithABrokenBackend(BaseDirdIntegrationTest):

    asset = 'broken_backend_config'

    def test_with_a_broken_backend(self):
        result = self.lookup('lice', 'default')

        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None, 'source_entry_id': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))
        assert_that(self.dird_logs(), contains_string('Failed to load back-end'))
        assert_that(self.dird_logs(), contains_string('has no name'))


class TestDisplay(BaseDirdIntegrationTest):

    asset = 'csv_with_multiple_displays'

    def test_that_the_display_is_really_applied_to_lookup(self):
        result = self.lookup('lice', 'default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number', None))
        assert_that(result['column_types'], contains(None, None, None, 'favorite'))

    def test_display_with_a_type_only(self):
        result = self.lookup('lice', 'test')

        assert_that(result['column_headers'], contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'], contains('firstname', None, None, 'status', None))
        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'AAA', None, None, 'Default'))

    def test_that_the_display_is_applied_to_headers(self):
        result = self.headers('default')

        assert_that(result['column_headers'], contains('Firstname', 'Lastname', 'Number', None))
        assert_that(result['column_types'], contains(None, None, None, 'favorite'))

    def test_display_on_headers_with_no_title(self):
        result = self.headers('test')

        assert_that(result['column_headers'],
                    contains('fn', 'ln', 'Empty', None, 'Default'))
        assert_that(result['column_types'],
                    contains('firstname', None, None, 'status', None))


class TestConfigurationWithNoPlugins(BaseDirdIntegrationTest):

    asset = 'no_plugins'

    def test_that_dird_does_not_run_when_not_configured(self):
        self._assert_no_docker_image_running(self.container_name)

    def _assert_no_docker_image_running(self, name):
        assert_that(name, is_not(is_in(sh.docker('ps'))))


class TestWithAnotherConfigDir(BaseDirdIntegrationTest):

    asset = 'in_plugins_d'

    def test_that_dird_can_load_source_plugins_in_another_dir(self):
        result = self.lookup('lice', 'default')

        expected_results = [
            {'column_values': ['Alice', 'AAA', '5555555555'],
             'source': 'my_csv',
             'relations': {'xivo_id': None, 'user_id': None,
                           'endpoint_id': None, 'agent_id': None,
                           'source_entry_id': None}},
        ]

        assert_that(result['results'],
                    contains_inanyorder(*expected_results))


class Test404WhenUnknownProfile(BaseDirdIntegrationTest):

    asset = 'sample_backend'

    def test_that_lookup_returns_404(self):
        result = self.get_lookup_result('lice', 'unknown', token=VALID_TOKEN)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(error['reason'], contains(all_of(contains_string('profile'),
                                                     contains_string('unknown'))))

    def test_that_headers_returns_404(self):
        result = self.get_headers_result('unknown', token=VALID_TOKEN)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(error['reason'], contains(all_of(contains_string('profile'),
                                                     contains_string('unknown'))))

    def test_that_favorites_returns_404(self):
        result = self.get_favorites_result('unknown', token=VALID_TOKEN)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(error['reason'], contains(all_of(contains_string('profile'),
                                                     contains_string('unknown'))))

    def test_that_personal_returns_404(self):
        result = self.get_personal_with_profile_result('unknown', token=VALID_TOKEN)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(error['reason'], contains(all_of(contains_string('profile'),
                                                     contains_string('unknown'))))
