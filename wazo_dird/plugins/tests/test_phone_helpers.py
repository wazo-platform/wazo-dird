# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from unittest import TestCase
from hamcrest import (
    assert_that,
    contains_inanyorder,
    empty,
    has_entries,
    has_properties,
)
from mock import (
    Mock,
    patch,
    sentinel as s,
)
from wazo_dird import make_result_class
from wazo_dird.exception import ProfileNotFoundError
from wazo_dird.plugins.phone_helpers import (
    _PhoneFormattedResult,
    _PhoneLookupService,
    _PhoneResultFormatter as Formatter,
)

Result = make_result_class('test')


@patch('wazo_dird.plugins.phone_helpers._PhoneResultFormatter')
class TestPhoneLookupService(TestCase):

    def setUp(self):
        self.formatted_results = [
            _PhoneFormattedResult('Alice', '1'),
            _PhoneFormattedResult('Bob', '2'),
            _PhoneFormattedResult('Carol', '3'),
        ]
        self.profile = 'profile1'
        self.formatter = Mock(Formatter)
        self.formatter.format_results.return_value = self.formatted_results

        self.display_service = Mock()
        self.lookup_service = Mock()
        display = {'name': 'display_name', 'columns': []}
        profile_to_display_phone = {
            'profile1': 'display_name',
        }
        self.display_service.list_.return_value = [display]

        self.phone_lookup_service = _PhoneLookupService(
            self.lookup_service,
            self.display_service,
            profile_to_display_phone,
        )

    def test_lookup(self, Formatter):
        formatted_results = [
            _PhoneFormattedResult('Bob', '2'),
            _PhoneFormattedResult('Alice', '1'),
        ]
        formatter = Formatter.return_value = Mock()
        # return a copy of formatted_results to test that sorting works
        formatter.format_results.side_effect = lambda _: list(formatted_results)

        results = self.phone_lookup_service.lookup('foo', self.profile, s.uuid, s.token)

        assert_that(results, has_entries(
            results=sorted(formatted_results),
        ))
        self.lookup_service.lookup.assert_called_once_with('foo', self.profile, s.uuid, {}, s.token)
        formatter.format_results.assert_called_once_with(self.lookup_service.lookup.return_value)

    def test_lookup_raise_when_unknown_profile(self, _):
        self.assertRaises(
            ProfileNotFoundError,
            self.phone_lookup_service.lookup, 'foo', 'unknown_profile', s.uuid, s.token,
        )

    def test_lookup_limit(self, Formatter):
        Formatter.return_value = self.formatter

        limit = 1

        results = self.phone_lookup_service.lookup('foo', self.profile, s.uuid, s.token, limit)

        assert_that(results, has_entries(
            results=self.formatted_results[:1],
            limit=limit,
        ))

    def test_lookup_offset(self, Formatter):
        Formatter.return_value = self.formatter

        offset = 1
        limit = 1

        results = self.phone_lookup_service.lookup(
            'foo', self.profile, s.uuid, s.token, limit, offset,
        )

        assert_that(results, has_entries(
            results=self.formatted_results[1:2],
            offset=offset,
            previous_offset=0,
            next_offset=2,
        ))

    def test_lookup_return_no_next_offset_when_has_no_more_results(self, Formatter):
        Formatter.return_value = self.formatter

        offset = 0
        limit = len(self.formatted_results)

        results = self.phone_lookup_service.lookup(
            'foo', self.profile, s.uuid, s.token, limit, offset,
        )

        assert_that(results, has_entries(
            results=self.formatted_results,
            next_offset=None,
        ))

    def test_lookup_return_no_previous_offset_when_has_no_previous_results(self, Formatter):
        Formatter.return_value = self.formatter

        results = self.phone_lookup_service.lookup('foo', self.profile, s.uuid, s.token)

        assert_that(results, has_entries(
            results=self.formatted_results,
            previous_offset=None,
        ))


class TestResultFormater(TestCase):

    def setUp(self):
        self.display = {
            'name': 'my display',
            'columns': [
                {
                    'field': 'number1',
                    'number_display': '{name1}',
                    'type': 'number',
                },
            ]
        }
        self.formatter = Formatter(self.display)

    def test_format_results(self):
        raw_results = [{'name1': 'John', 'number1': '1'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            ('John', '1'),
        ))

    def test_format_results_return_strip_number(self):
        raw_results = [{'name1': 'John', 'number1': '1(418)-555.1234'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            ('John', '14185551234'),
        ))

    def test_format_results_return_none_when_number_with_unauthorized_characters(self):
        raw_results = [{'name1': 'John', 'number1': '()abcd'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, empty())

    def test_format_results_return_special_number_when_pattern_matchs(self):
        raw_results = [{'name1': 'John', 'number1': '+33(0)123456789'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            ('John', '0033123456789'),
        ))

    def test_format_results_return_number_with_special_characters(self):
        raw_results_1 = [{'name1': 'John', 'number1': '*10'}]
        lookup_results_1 = [Result(raw_result) for raw_result in raw_results_1]
        results_1 = self.formatter.format_results(lookup_results_1)

        raw_results_2 = [{'name1': 'John', 'number1': '#10'}]
        lookup_results_2 = [Result(raw_result) for raw_result in raw_results_2]
        results_2 = self.formatter.format_results(lookup_results_2)

        raw_results_3 = [{'name1': 'John', 'number1': '+10'}]
        lookup_results_3 = [Result(raw_result) for raw_result in raw_results_3]
        results_3 = self.formatter.format_results(lookup_results_3)

        assert_that(results_1, contains_inanyorder(('John', '*10')))
        assert_that(results_2, contains_inanyorder(('John', '#10')))
        assert_that(results_3, contains_inanyorder(('John', '+10')))

    def test_results_have_attributes(self):
        raw_results = [{'name1': 'John', 'number1': '1'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            has_properties(name='John', number='1'),
        ))

    def test_format_results_no_name(self):
        raw_results = [{'number1': '1'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, empty())

    def test_format_results_no_number(self):
        raw_results = [{'name1': 'John'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = self.formatter.format_results(lookup_results)

        assert_that(results, empty())

    def test_format_results_multiple(self):
        display = {
            'name': 'my display',
            'columns': [
                {
                    'field': 'number',
                    'number_display': '{name}',
                    'type': 'number',
                },
                {
                    'field': 'mobile',
                    'number_display': '{name}',
                    'type': 'number',
                },
            ],
        }
        formatter = Formatter(display)

        raw_results = [{'name': 'John', 'number': '1', 'mobile': '3'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            ('John', '1'),
            ('John', '3'),
        ))

    def test_format_results_multiple_missing_first(self):
        display = {
            'name': 'my display',
            'columns': [
                {
                    'field': 'number',
                    'number_display': '{name}',
                    'type': 'number',
                },
                {
                    'field': 'mobile',
                    'number_display': '{name}',
                    'type': 'number',
                },
            ],
        }
        formatter = Formatter(display)

        raw_results = [{'name': 'John', 'mobile': '3'}]
        lookup_results = [Result(raw_result) for raw_result in raw_results]

        results = formatter.format_results(lookup_results)

        assert_that(results, contains_inanyorder(
            ('John', '3'),
        ))
