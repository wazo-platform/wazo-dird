# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    all_of,
    any_of,
    assert_that,
    contains,
    contains_inanyorder,
    contains_string,
    equal_to,
    has_entries,
    has_length,
)

from .helpers.base import (
    BaseDirdIntegrationTest,
    CSVWithMultipleDisplayTestCase,
    HalfBrokenTestCase,
)
from .helpers.config import new_multiple_sources_config
from .helpers.constants import VALID_TOKEN_MAIN_TENANT, VALID_UUID

EMPTY_RELATIONS = {
    'xivo_id': None,
    'user_id': None,
    'user_uuid': None,
    'endpoint_id': None,
    'agent_id': None,
    'source_entry_id': None,
}


class BaseMultipleSourceLauncher(BaseDirdIntegrationTest):
    asset = 'multiple_sources'
    config_factory = new_multiple_sources_config


class TestSourceModification(BaseMultipleSourceLauncher):
    def test_source_update(self):
        response = self.lookup('alan', 'default')
        assert_that(
            response,
            has_entries(
                results=contains(
                    has_entries(column_values=contains('Alice', 'Alan', '1111'))
                )
            ),
        )

        source = self.client.csv_source.list(name='third_csv')['items'][0]
        source['format_columns']['firstname'] = 'SUCCESS {firstname}'
        self.client.csv_source.edit(source['uuid'], source)

        response = self.lookup('alan', 'default')
        assert_that(
            response,
            has_entries(
                results=contains(
                    has_entries(column_values=contains('SUCCESS Alice', 'Alan', '1111'))
                )
            ),
        )


class TestCoreSourceManagement(BaseMultipleSourceLauncher):
    alice_aaa = {
        'column_values': ['Alice', 'AAA', '5555555555'],
        'source': 'my_csv',
        'backend': 'csv',
        'relations': EMPTY_RELATIONS,
    }
    alice_alan = {
        'column_values': ['Alice', 'Alan', '1111'],
        'source': 'third_csv',
        'backend': 'csv',
        'relations': {
            'xivo_id': None,
            'user_id': None,
            'user_uuid': None,
            'endpoint_id': None,
            'agent_id': None,
            'source_entry_id': '1',
        },
    }

    def test_multiple_source_from_the_same_backend(self):
        result = self.lookup('lice', 'default')

        # second_csv does not search in column firstname
        assert_that(
            result['results'], contains_inanyorder(self.alice_aaa, self.alice_alan)
        )


class TestReverse(BaseMultipleSourceLauncher):
    def setUp(self):
        super().setUp()
        self.alice_expected_fields = {
            'clientno': '1',
            'firstname': 'Alice',
            'lastname': 'Alan',
            'number': '1111',
            'mobile': '11112',
            'reverse': 'Alice Alan',
        }
        self.qwerty_expected_fields = {
            'fn': 'qwerty',
            'ln': 'azerty',
            'num': '1111',
            'firstname': 'qwerty',
            'lastname': 'azerty',
            'number': '1111',
            'reverse': 'qwerty azerty',
        }
        self.alice_result = {
            'display': 'Alice Alan',
            'exten': '1111',
            'source': 'third_csv',
            'fields': self.alice_expected_fields,
        }
        self.qwerty_result_1 = {
            'display': 'qwerty azerty',
            'exten': '1111',
            'source': 'my_csv',
            'fields': self.qwerty_expected_fields,
        }
        self.qwerty_result_2 = {
            'display': 'qwerty azerty',
            'exten': '1111',
            'source': 'second_csv',
            'fields': self.qwerty_expected_fields,
        }

    def test_reverse_when_no_result(self):
        result = self.reverse('1234', 'default', VALID_UUID)

        expected = {'display': None, 'exten': '1234', 'source': None, 'fields': {}}

        assert_that(result, equal_to(expected))

    def test_reverse_with_user_uuid(self):
        result = self.get_reverse_result(
            '1111', 'default', VALID_UUID, VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to(200))

    def test_reverse_when_multi_result(self):
        result = self.reverse('1111', 'default', VALID_UUID)

        assert_that(
            result,
            any_of(self.alice_result, self.qwerty_result_1, self.qwerty_result_2),
        )

    def test_reverse_when_multi_columns(self):
        result = self.reverse('11112', 'default', VALID_UUID)

        expected = {
            'display': 'Alice Alan',
            'exten': '11112',  # <-- matches the mobile
            'source': 'third_csv',
            'fields': self.alice_expected_fields,
        }

        assert_that(result, equal_to(expected))


class TestLookupWhenASourceFails(HalfBrokenTestCase):
    def test_that_lookup_returns_some_results(self):
        result = self.lookup('al', 'default')

        assert_that(result['results'], has_length(2))
        assert_that(
            result['results'][0]['column_values'],
            contains('Alice', 'AAA', '5555555555'),
        )
        assert_that(
            result['results'][1]['column_values'],
            contains('Alice', 'AAA', '5555555555'),
        )

    def test_that_reverse_returns_a_result(self):
        result = self.reverse('5555555555', 'default', VALID_UUID)

        assert_that(
            result, has_entries({'display': 'Second Lookup', 'exten': '5555555555'})
        )


class TestDisplay(CSVWithMultipleDisplayTestCase):
    def test_that_the_display_is_really_applied_to_lookup(self):
        result = self.lookup('lice', 'default')

        assert_that(
            result['column_headers'], contains('Firstname', 'Lastname', 'Number', None)
        )
        assert_that(result['column_types'], contains(None, None, None, 'favorite'))

    def test_display_with_a_type_only(self):
        result = self.lookup('lice', 'test')

        assert_that(
            result['column_headers'], contains('fn', 'ln', 'Empty', None, 'Default')
        )
        assert_that(
            result['column_types'], contains('firstname', None, None, 'status', None)
        )
        assert_that(
            result['results'][0]['column_values'],
            contains('Alice', 'AAA', None, None, 'Default'),
        )

    def test_that_the_display_is_applied_to_headers(self):
        result = self.headers('default')

        assert_that(
            result['column_headers'], contains('Firstname', 'Lastname', 'Number', None)
        )
        assert_that(result['column_types'], contains(None, None, None, 'favorite'))

    def test_display_on_headers_with_no_title(self):
        result = self.headers('test')

        assert_that(
            result['column_headers'], contains('fn', 'ln', 'Empty', None, 'Default')
        )
        assert_that(
            result['column_types'], contains('firstname', None, None, 'status', None)
        )


class Test404WhenUnknownProfile(CSVWithMultipleDisplayTestCase):
    def test_that_lookup_returns_404(self):
        result = self.get_lookup_result(
            'lice', 'unknown', token=VALID_TOKEN_MAIN_TENANT
        )

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(
            error['reason'],
            contains(all_of(contains_string('profile'), contains_string('unknown'))),
        )

    def test_that_headers_returns_404(self):
        result = self.get_headers_result('unknown', token=VALID_TOKEN_MAIN_TENANT)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(
            error['reason'],
            contains(all_of(contains_string('profile'), contains_string('unknown'))),
        )

    def test_that_favorites_returns_404(self):
        result = self.get_favorites_result('unknown', token=VALID_TOKEN_MAIN_TENANT)

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(
            error['reason'],
            contains(all_of(contains_string('profile'), contains_string('unknown'))),
        )

    def test_that_personal_returns_404(self):
        result = self.get_personal_with_profile_result(
            'unknown', token=VALID_TOKEN_MAIN_TENANT
        )

        error = result.json()

        assert_that(result.status_code, equal_to(404))
        assert_that(
            error['reason'],
            contains(all_of(contains_string('profile'), contains_string('unknown'))),
        )
