# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from hamcrest import assert_that, contains_inanyorder
from mock import Mock, ANY, sentinel, patch
from xivo_dird.plugins.base_plugins import BaseSourcePlugin
from xivo_dird.plugins.phonebook_plugin import _PhonebookConfig, \
    _PhonebookResultConverter, _PhonebookClient, PhonebookPlugin, _PhonebookFactory
from xivo_dird.plugins.source_result import make_result_class


class TestPhonebookPlugin(unittest.TestCase):

    def setUp(self):
        self.config = {'config': sentinel}
        self.pbook_config = Mock(_PhonebookConfig)
        self.pbook_result_converter = Mock(_PhonebookResultConverter)
        self.pbook_client = Mock(_PhonebookClient)
        self.pbook_factory = Mock(_PhonebookFactory)
        self.pbook_factory.new_phonebook_config.return_value = self.pbook_config
        self.pbook_factory.new_phonebook_result_converter.return_value = self.pbook_result_converter
        self.pbook_factory.new_phonebook_client.return_value = self.pbook_client
        self.pbook_plugin = PhonebookPlugin()
        self.pbook_plugin.pbook_factory = self.pbook_factory

    def test_load(self):
        self.pbook_plugin.load(self.config)

        self.pbook_factory.new_phonebook_config.assert_called_once_with(self.config['config'])
        self.pbook_factory.new_phonebook_result_converter.assert_called_once_with(self.pbook_config)
        self.pbook_factory.new_phonebook_client.assert_called_once_with(self.pbook_config)

    def test_search(self):
        term = u'foobar'
        self.pbook_client.search.return_value = sentinel.search_result
        self.pbook_result_converter.convert_all.return_value = sentinel.convert_all_result

        self.pbook_plugin.load(self.config)
        result = self.pbook_plugin.search(term)

        self.pbook_client.search.assert_called_once_with(term.encode('UTF-8'))
        self.pbook_result_converter.convert_all.assert_called_once_with(sentinel.search_result)
        self.assertIs(result, sentinel.convert_all_result)

    def test_first_match(self):
        exten = u'123456'
        self.pbook_client.first_match.return_value = sentinel.first_match_result
        self.pbook_result_converter.convert.return_value = sentinel.convert_result

        self.pbook_plugin.load(self.config)
        result = self.pbook_plugin.first_match(exten)

        self.pbook_client.first_match.assert_called_once_with(exten.encode('UTF-8'))
        self.pbook_result_converter.convert.assert_called_once_with(sentinel.first_match_result)
        self.assertIs(result, sentinel.convert_result)


class _TestPhonebookFactory(unittest.TestCase):

    def setUp(self):
        self.pbook_factory = _PhonebookFactory()

    def test_phonebook_config(self):
        phonebook_config = self.pbook_factory.new_phonebook_config({})

        self.assertIsInstance(phonebook_config, _PhonebookConfig)

    def test_phonebook_client(self):
        phonebook_client = self.pbook_factory.new_phonebook_client(sentinel.pbook_config)

        self.assertIsInstance(phonebook_client, _PhonebookClient)

    def test_phonebook_result_converter(self):
        phonebook_result_converter = self.pbook_factory.new_phonebook_result_converter(sentinel.pbook_config)

        self.assertIsInstance(phonebook_result_converter, _PhonebookResultConverter)


class TestPhonebookConfig(unittest.TestCase):

    def test_name(self):
        value = 'foo'

        phonebook_config = _PhonebookConfig({'name': value})

        self.assertEqual(value, phonebook_config.name())

    def test_name_when_absent(self):
        phonebook_config = _PhonebookConfig({})

        self.assertRaises(Exception, phonebook_config.name)

    def test_format_columns(self):
        value = {'firstname': '{phonebook.firstname}'}

        phonebook_config = _PhonebookConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: value,
        })

        self.assertEqual(value, phonebook_config.format_columns())

    def test_format_columns_when_absent(self):
        phonebook_config = _PhonebookConfig({})

        self.assertRaises(Exception, phonebook_config.format_columns)

    def test_first_matched_columns(self):
        value = ['phonebook.exten']

        phonebook_config = _PhonebookConfig({
            BaseSourcePlugin.FIRST_MATCHED_COLUMNS: value,
        })

        self.assertEqual(value, phonebook_config.first_matched_columns())

    def test_first_matched_columns_when_absent(self):
        phonebook_config = _PhonebookConfig({})

        self.assertRaises(Exception, phonebook_config.first_matched_columns)

    def test_looked_up_keys(self):
        value = {'firstname': '{phonebook.firstname}',
                 'name': '{phonebook.firstname} {phonebook.lastname}'}

        phonebook_config = _PhonebookConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: value,
        })

        assert_that(phonebook_config.looked_up_keys(),
                    contains_inanyorder('phonebook.firstname', 'phonebook.lastname'))

    def test_phonebook_url(self):
        value = 'http://example.org/foobar'

        phonebook_config = _PhonebookConfig({'phonebook_url': value})

        self.assertEqual(value, phonebook_config.phonebook_url())

    def test_phonebook_url_when_absent(self):
        phonebook_config = _PhonebookConfig({})

        self.assertEqual(_PhonebookConfig.DEFAULT_PHONEBOOK_URL, phonebook_config.phonebook_url())

    def test_phonebook_username(self):
        value = 'john'

        phonebook_config = _PhonebookConfig({'phonebook_username': value})

        self.assertEqual(value, phonebook_config.phonebook_username())

    def test_phonebook_password(self):
        value = 'foobar'

        phonebook_config = _PhonebookConfig({'phonebook_password': value})

        self.assertEqual(value, phonebook_config.phonebook_password())

    def test_phonebook_timeout(self):
        value = 4.0

        phonebook_config = _PhonebookConfig({'phonebook_timeout': value})

        self.assertEqual(value, phonebook_config.phonebook_timeout())


class TestPhonebookClient(unittest.TestCase):

    def setUp(self):
        self.url = 'http://example.org'
        self.username = 'admin'
        self.password = 'foobar'
        self.timeout = 1.1
        self.first_matched_columns = ['phonebook.exten', 'phonebook.office']
        self.pbook_config = Mock(_PhonebookConfig)
        self.pbook_config.phonebook_url.return_value = self.url
        self.pbook_config.phonebook_username.return_value = self.username
        self.pbook_config.phonebook_password.return_value = self.password
        self.pbook_config.phonebook_timeout.return_value = self.timeout
        self.pbook_config.first_matched_columns.return_value = self.first_matched_columns
        self.pbook_client = _PhonebookClient(self.pbook_config)

    @patch('xivo_dird.plugins.phonebook_plugin.requests')
    def test_search(self, mock_requests):
        response = Mock()
        response.status_code = 200
        response.json.return_value = sentinel.json
        mock_requests.get.return_value = response

        result = self.pbook_client.search('foo')

        mock_requests.get.assert_called_once_with(self.url,
                                                  auth=ANY,
                                                  params={'act': 'search', 'search': 'foo'},
                                                  timeout=self.timeout, verify=False)
        response.json.assert_called_once_with()
        self.assertIs(result, sentinel.json)

    @patch('xivo_dird.plugins.phonebook_plugin.requests')
    def test_search_on_http_204(self, mock_requests):
        response = Mock()
        response.status_code = 204
        mock_requests.get.return_value = response

        result = self.pbook_client.search('foo')

        self.assertFalse(response.json.called)
        self.assertEqual(result, [])

    @patch('xivo_dird.plugins.phonebook_plugin.requests')
    def test_search_on_http_401(self, mock_requests):
        response = Mock()
        response.status_code = 401
        mock_requests.get.return_value = response

        result = self.pbook_client.search('foo')

        self.assertFalse(response.json.called)
        self.assertEqual(result, [])

    @patch('xivo_dird.plugins.phonebook_plugin.requests')
    def test_search_on_requests_exception(self, mock_requests):
        mock_requests.get.side_effect = Exception('test')

        result = self.pbook_client.search('foo')

        self.assertEqual(result, [])

    def test_first_match_return_None_if_no_match(self):
        self.pbook_client.search = Mock()
        self.pbook_client.search.return_value = []

        result = self.pbook_client.first_match('123456')
        self.assertIs(result, None)

    def test_new_auth(self):
        auth = self.pbook_client._new_auth(self.pbook_config)

        self.assertIsNotNone(auth)

    def test_new_auth_when_no_username(self):
        self.pbook_config.phonebook_username.return_value = None
        self.pbook_config.phonebook_password.return_value = None

        auth = self.pbook_client._new_auth(self.pbook_config)

        self.assertIsNone(auth)


class TestPhonebookResultConverter(unittest.TestCase):

    def setUp(self):
        self.name = 'foo'
        self.format_columns = {
            'name': '{phonebook.firstname} {phonebook.lastname}',
            'firstname': '{phonebook.firstname}',
            'lastname': '{phonebook.lastname}',
            'number': '{phonebooknumber.office.number}',
        }
        self.pbook_config = Mock(_PhonebookConfig)
        self.pbook_config.name.return_value = self.name
        self.pbook_config.format_columns.return_value = self.format_columns
        self.pbook_config.looked_up_keys.return_value = ['phonebook.firstname',
                                                         'phonebook.lastname',
                                                         'phonebooknumber.office.number']
        self.pbook_result_converter = _PhonebookResultConverter(self.pbook_config)
        self.SourceResult = make_result_class(self.name, None, None)

    def test_convert(self):
        raw_result = {
            'phonebook': {
                'firstname': 'Alice',
                'lastname': 'Wonder',
                'displayname': 'Alice Wonder',
            },
            'phonebooknumber': {
                'office': {
                    'number': '111',
                }
            },
        }
        expected_result = self.SourceResult({'firstname': 'Alice',
                                             'lastname': 'Wonder',
                                             'name': 'Alice Wonder',
                                             'number': '111'})

        result = self.pbook_result_converter.convert(raw_result)

        self.assertEqual(expected_result, result)

    def test_convert_value_false_doesnt_raise(self):
        raw_result = {
            'phonebook': {
                'firstname': u'Éric',
                'lastname': 'Wonder',
            },
            'phonebooknumber': False,
        }
        expected_result = self.SourceResult({'firstname': u'Éric',
                                             'lastname': 'Wonder',
                                             'name': u'Éric Wonder',
                                             'number': None})

        result = self.pbook_result_converter.convert(raw_result)

        self.assertEqual(expected_result, result)

    def test_convert_missing_key_doesnt_raise(self):
        raw_result = {
            'phonebook': {
                'firstname': 'Alice',
            },
        }
        expected_result = self.SourceResult({'firstname': 'Alice',
                                             'lastname': None,
                                             'name': 'Alice',
                                             'number': None})

        result = self.pbook_result_converter.convert(raw_result)

        self.assertEqual(expected_result, result)

    def test_convert_all(self):
        raw_results = [{
            'phonebook': {
                'firstname': 'Alice',
                'lastname': 'Wonder',
            },
        }]
        expected_results = [self.SourceResult({'firstname': 'Alice',
                                               'lastname': 'Wonder',
                                               'name': 'Alice Wonder',
                                               'number': None})]

        results = self.pbook_result_converter.convert_all(raw_results)

        self.assertEqual(expected_results, results)
