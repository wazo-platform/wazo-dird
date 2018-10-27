# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from hamcrest import assert_that, equal_to, is_
from mock import Mock, patch, sentinel
from unittest import TestCase
from wazo_dird.exception import InvalidConfigError, ProfileNotFoundError
from wazo_dird.plugins.phone_helpers import _PhoneFormattedResult, _PhoneLookupService,\
    _PhoneResultFormatter, _new_formatters_from_config


class TestPhoneLookupService(TestCase):

    def setUp(self):
        self.formatted_results = [
            _PhoneFormattedResult('Alice', '1'),
            _PhoneFormattedResult('Bob', '2'),
            _PhoneFormattedResult('Carol', '3'),
        ]
        self.profile = 'profile1'
        self.formatter = Mock(_PhoneResultFormatter)
        self.formatter.format_results.return_value = self.formatted_results
        self.formatters = {self.profile: self.formatter}
        self.lookup_service = Mock()
        self.phone_lookup_service = _PhoneLookupService(self.lookup_service, self.formatters)

    def test_lookup(self):
        formatted_results = [
            _PhoneFormattedResult('Bob', '2'),
            _PhoneFormattedResult('Alice', '1'),
        ]
        # return a copy of formatted_results to test that sorting works
        self.formatter.format_results.side_effect = lambda _: list(formatted_results)

        results = self.phone_lookup_service.lookup('foo', self.profile, sentinel.uuid, sentinel.token)

        assert_that(results['results'], equal_to(sorted(formatted_results)))
        self.lookup_service.lookup.assert_called_once_with('foo', self.profile, sentinel.uuid, {}, sentinel.token)
        self.formatter.format_results.assert_called_once_with(self.lookup_service.lookup.return_value)

    def test_lookup_raise_when_unknown_profile(self):
        self.assertRaises(ProfileNotFoundError,
                          self.phone_lookup_service.lookup, 'foo', 'unknown_profile', sentinel.uuid, sentinel.token)

    def test_lookup_limit(self):
        limit = 1

        results = self.phone_lookup_service.lookup('foo', self.profile, sentinel.uuid, sentinel.token, limit)

        assert_that(results['results'], equal_to(self.formatted_results[:1]))
        assert_that(results['limit'], equal_to(limit))

    def test_lookup_offset(self):
        offset = 1
        limit = 1

        results = self.phone_lookup_service.lookup('foo', self.profile, sentinel.uuid, sentinel.token, limit, offset)

        assert_that(results['results'], equal_to(self.formatted_results[1:2]))
        assert_that(results['offset'], equal_to(offset))
        assert_that(results['previous_offset'], equal_to(0))
        assert_that(results['next_offset'], equal_to(2))

    def test_lookup_return_no_next_offset_when_has_no_more_results(self):
        offset = 0
        limit = len(self.formatted_results)

        results = self.phone_lookup_service.lookup('foo', self.profile, sentinel.uuid, sentinel.token, limit, offset)

        assert_that(results['results'], equal_to(self.formatted_results))
        assert_that(results['next_offset'], is_(None))

    def test_lookup_return_no_previous_offset_when_has_no_previous_results(self):
        results = self.phone_lookup_service.lookup('foo', self.profile, sentinel.uuid, sentinel.token)

        assert_that(results['results'], equal_to(self.formatted_results))
        assert_that(results['previous_offset'], is_(None))


class TestPhoneResultFormatter(TestCase):

    def setUp(self):
        self.name = ['name1', 'name2']
        self.number = [
            {
                'field': ['number1', 'number2'],
            }
        ]
        self.config = {
            'name': self.name,
            'number': self.number,
        }

    def test_format_results(self):
        fields = {
            'name1': 'John',
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '1')]))

    def test_format_results_return_strip_number(self):
        fields = {
            'name1': 'John',
            'number1': '1(418)-555.1234',
        }
        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '14185551234')]))

    def test_format_results_return_none_when_number_with_unauthorized_characters(self):
        fields = {
            'name1': 'John',
            'number1': '()abcd',
        }
        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([]))

    def test_format_results_return_special_number_when_pattern_matchs(self):
        fields = {
            'name1': 'John',
            'number1': '+33(0)123456789',
        }
        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '0033123456789')]))

    def test_format_results_return_number_with_special_characters(self):
        fields1 = {
            'name1': 'John',
            'number1': '*10',
        }
        formatted_results1 = self._format_results(fields1)

        fields2 = {
            'name1': 'John',
            'number1': '#10',
        }
        formatted_results2 = self._format_results(fields2)

        fields3 = {
            'name1': 'John',
            'number1': '+10',
        }

        formatted_results3 = self._format_results(fields3)

        assert_that(formatted_results1, equal_to([('John', '*10')]))
        assert_that(formatted_results2, equal_to([('John', '#10')]))
        assert_that(formatted_results3, equal_to([('John', '+10')]))

    def test_results_have_attributes(self):
        fields = {
            'name1': 'John',
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results[0].name, equal_to('John'))
        assert_that(formatted_results[0].number, equal_to('1'))

    def test_format_results_use_fallback_name(self):
        fields = {
            'name2': 'James',
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('James', '1')]))

    def test_format_results_use_fallback_name_when_name_is_false(self):
        fields = {
            'name1': '',
            'name2': 'James',
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('James', '1')]))

    def test_format_results_no_name(self):
        fields = {
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([]))

    def test_format_results_use_fallback_number(self):
        fields = {
            'name1': 'John',
            'number2': '2',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '2')]))

    def test_format_results_no_number(self):
        fields = {
            'name1': 'John',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([]))

    def test_format_results_multiple(self):
        self.number.append({
            'field': ['mobile1', 'mobile2']
        })
        fields = {
            'name1': 'John',
            'number1': '1',
            'mobile1': '3',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '1'), ('John', '3')]))

    def test_format_results_multiple_missing_first(self):
        self.number.append({
            'field': ['mobile1', 'mobile2']
        })
        fields = {
            'name1': 'John',
            'mobile1': '3',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John', '3')]))

    def test_format_results_with_name_format(self):
        self.number[0]['name_format'] = '{name}-{number}'
        fields = {
            'name1': 'John',
            'number1': '1',
        }

        formatted_results = self._format_results(fields)

        assert_that(formatted_results, equal_to([('John-1', '1')]))

    def test_new_from_config(self):
        config = {
            'name': [
                'name1',
                'name2',
            ],
            'number': [
                {
                    'field': [
                        'phone',
                        'phone1'
                    ],
                    'name_format': '{name}',
                }
            ]
        }

        formatter = _PhoneResultFormatter.new_from_config(config)

        assert_that(formatter._name_config, equal_to(config['name']))
        assert_that(formatter._number_config, equal_to(config['number']))

    def test_new_from_config_invalid_type(self):
        config = None

        self._assert_invalid_config(config, 'views/displays_phone')

    def test_new_from_config_missing_name_key(self):
        del self.config['name']

        self._assert_invalid_config(self.config, 'views/displays_phone')

    def test_new_from_config_missing_number_key(self):
        del self.config['number']

        self._assert_invalid_config(self.config, 'views/displays_phone')

    def test_new_from_config_name_invalid_type(self):
        self.config['name'] = 'foo'

        self._assert_invalid_config(self.config, 'views/displays_phone/name')

    def test_new_from_config_name_invalid_length(self):
        self.config['name'] = []

        self._assert_invalid_config(self.config, 'views/displays_phone/name')

    def test_new_from_config_name_item_invalid_type(self):
        self.config['name'] = [None]

        self._assert_invalid_config(self.config, 'views/displays_phone/name/0')

    def test_new_from_config_number_invalid_type(self):
        self.config['number'] = None

        self._assert_invalid_config(self.config, 'views/displays_phone/number')

    def test_new_from_config_number_invalid_length(self):
        self.config['number'] = []

        self._assert_invalid_config(self.config, 'views/displays_phone/number')

    def test_new_from_config_number_item_invalid_type(self):
        self.config['number'] = [None]

        self._assert_invalid_config(self.config, 'views/displays_phone/number/0')

    def test_new_from_config_number_item_missing_field_key(self):
        self.config['number'] = [{}]

        self._assert_invalid_config(self.config, 'views/displays_phone/number/0')

    def test_new_from_config_number_item_invalid_field_key_type(self):
        self.config['number'] = [{'field': 'lol'}]

        self._assert_invalid_config(self.config, 'views/displays_phone/number/0/field')

    def test_new_from_config_number_item_invalid_field_key_item_type(self):
        self.config['number'] = [{'field': [None]}]

        self._assert_invalid_config(self.config, 'views/displays_phone/number/0/field/0')

    def test_new_from_config_number_item_invalid_name_format_key_type(self):
        self.config['number'] = [{'field': ['a'], 'name_format': {}}]

        self._assert_invalid_config(self.config, 'views/displays_phone/number/0/name_format')

    def _format_results(self, fields):
        formatter = _PhoneResultFormatter(self.name, self.number)
        lookup_result = Mock()
        lookup_result.fields = fields
        return formatter.format_results([lookup_result])

    def _assert_invalid_config(self, config, location_path):
        try:
            _PhoneResultFormatter.new_from_config(config)
        except InvalidConfigError as e:
            assert_that(e.location_path, equal_to(location_path))
        else:
            self.fail('InvalidConfigError not raised')


class TestNewFormattersFromConfig(TestCase):

    def setUp(self):
        self.config = {
            'displays_phone': {},
        }

    @patch('wazo_dird.plugins.phone_helpers._PhoneResultFormatter')
    def test_new_from_config(self, mock_Display):
        views_config = {
            'displays_phone': {
                'default': sentinel.default_display,
            },
            'profile_to_display_phone': {
                'foo': 'default',
            }
        }

        formatters = _new_formatters_from_config(views_config)

        mock_Display.new_from_config.assert_called_once_with(sentinel.default_display)
        assert_that(formatters, equal_to({'foo': mock_Display.new_from_config.return_value}))

    def test_new_from_config_invalid_type(self):
        config = None

        self._assert_invalid_config(config, 'views')

    def test_new_from_config_missing_displays_phone_key(self):
        del self.config['displays_phone']

        self._assert_invalid_config(self.config, 'views')

    def test_new_from_config_displays_phone_invalid_type(self):
        self.config['displays_phone'] = 'foo'

        self._assert_invalid_config(self.config, 'views/displays_phone')

    def test_new_from_config_profile_to_display_phone_invalid_type(self):
        self.config['profile_to_display_phone'] = 'foo'

        self._assert_invalid_config(self.config, 'views/profile_to_display_phone')

    def test_new_from_config_profile_to_display_phone_invalid_item_type(self):
        self.config['profile_to_display_phone'] = {'default': None}

        self._assert_invalid_config(self.config, 'views/profile_to_display_phone/default')

    def test_new_from_config_profile_to_display_phone_missing_display(self):
        self.config['profile_to_display_phone'] = {'foo': 'anchovy'}

        self._assert_invalid_config(self.config, 'views/profile_to_display_phone/foo')

    def _assert_invalid_config(self, config, location_path):
        try:
            _new_formatters_from_config(config)
        except InvalidConfigError as e:
            assert_that(e.location_path, equal_to(location_path))
        else:
            self.fail('InvalidConfigError not raised')
