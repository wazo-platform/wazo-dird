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

from hamcrest import assert_that, equal_to
from mock import Mock, patch, sentinel
from unittest import TestCase
from xivo_dird.core.phone_helpers import _PhoneDisplay, _Display
from xivo_dird.core.exception import InvalidConfigError


class TestPhoneDisplay(TestCase):

    def setUp(self):
        self.display_name = 'display1'
        self.profile_name = 'profile1'
        self.display = Mock(_Display)
        self.display.format_results.return_value = [Mock()]
        self.lookup_results = [Mock()]
        self.config = {
            'displays_phone': {},
        }

    def test_format_results(self):
        displays = {
            self.display_name: self.display
        }
        profile_to_display = {
            self.profile_name: self.display_name,
        }
        phone_display = _PhoneDisplay(displays, profile_to_display)

        results = phone_display.format_results(self.profile_name, self.lookup_results)

        self.display.format_results.assert_called_once_with(self.lookup_results)
        assert_that(results, equal_to(self.display.format_results.return_value))

    def test_format_results_no_display_with_default_display(self):
        displays = {
            _PhoneDisplay.DEFAULT_DISPLAY_NAME: self.display
        }
        profile_to_display = {
            self.profile_name: self.display_name,
        }
        phone_display = _PhoneDisplay(displays, profile_to_display)

        phone_display.format_results(self.profile_name, self.lookup_results)

        self.display.format_results.assert_called_once_with(self.lookup_results)

    def test_format_results_no_profile_to_display_with_default_display(self):
        displays = {
            _PhoneDisplay.DEFAULT_DISPLAY_NAME: self.display
        }
        phone_display = _PhoneDisplay(displays, {})

        phone_display.format_results(self.profile_name, self.lookup_results)

        self.display.format_results.assert_called_once_with(self.lookup_results)

    @patch('xivo_dird.core.phone_helpers._Display')
    def test_new_from_config(self, mock_Display):
        views_config = {
            'displays_phone': {
                'default': sentinel.default_display,
            }
        }

        phone_display = _PhoneDisplay.new_from_config(views_config)

        mock_Display.new_from_config.assert_called_once_with(sentinel.default_display)
        assert_that(phone_display._displays, equal_to({'default': mock_Display.new_from_config.return_value}))
        assert_that(phone_display._profile_to_display, equal_to({}))

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

    def _assert_invalid_config(self, config, location_path):
        try:
            _PhoneDisplay.new_from_config(config)
        except InvalidConfigError as e:
            assert_that(e.location_path, equal_to(location_path))
        else:
            self.fail('InvalidConfigError not raised')


class TestDisplay(TestCase):

    def setUp(self):
        self.name = ['name1', 'name2']
        self.number = [{
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

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('John', '1')]))

    def test_results_have_attributes(self):
        fields = {
            'name1': 'John',
            'number1': '1',
        }

        display_results = self._format_results(fields)

        assert_that(display_results[0].name, equal_to('John'))
        assert_that(display_results[0].number, equal_to('1'))

    def test_format_results_use_fallback_name(self):
        fields = {
            'name2': 'James',
            'number1': '1',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('James', '1')]))

    def test_format_results_use_fallback_name_when_name_is_false(self):
        fields = {
            'name1': '',
            'name2': 'James',
            'number1': '1',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('James', '1')]))

    def test_format_results_no_name(self):
        fields = {
            'number1': '1',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([]))

    def test_format_results_use_fallback_number(self):
        fields = {
            'name1': 'John',
            'number2': '2',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('John', '2')]))

    def test_format_results_no_number(self):
        fields = {
            'name1': 'John',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([]))

    def test_format_results_multiple(self):
        self.number.append({
            'field': ['mobile1', 'mobile2']
        })
        fields = {
            'name1': 'John',
            'number1': '1',
            'mobile1': '3',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('John', '1'), ('John', '3')]))

    def test_format_results_multiple_missing_first(self):
        self.number.append({
            'field': ['mobile1', 'mobile2']
        })
        fields = {
            'name1': 'John',
            'mobile1': '3',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('John', '3')]))

    def test_format_results_with_name_format(self):
        self.number[0]['name_format'] = '{name}-{number}'
        fields = {
            'name1': 'John',
            'number1': '1',
        }

        display_results = self._format_results(fields)

        assert_that(display_results, equal_to([('John-1', '1')]))

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

        display = _Display.new_from_config(config)

        assert_that(display._name_config, equal_to(config['name']))
        assert_that(display._number_config, equal_to(config['number']))

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
        display = _Display(self.name, self.number)
        lookup_result = Mock()
        lookup_result.fields = fields
        return display.format_results([lookup_result])

    def _assert_invalid_config(self, config, location_path):
        try:
            _Display.new_from_config(config)
        except InvalidConfigError as e:
            assert_that(e.location_path, equal_to(location_path))
        else:
            self.fail('InvalidConfigError not raised')
