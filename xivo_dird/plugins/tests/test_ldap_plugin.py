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

import ldap
import unittest

from hamcrest import assert_that
from hamcrest import contains_inanyorder
from ldap.ldapobject import LDAPObject
from mock import Mock, ANY, sentinel
from xivo_dird.plugins.base_plugins import BaseSourcePlugin
from xivo_dird.plugins.ldap_plugin import _LDAPConfig, \
    _LDAPResultFormatter, _LDAPClient, LDAPPlugin, _LDAPFactory
from xivo_dird.plugins.source_result import make_result_class


class TestLDAPPlugin(unittest.TestCase):

    def setUp(self):
        self.config = {'config': sentinel}
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_result_formatter = Mock(_LDAPResultFormatter)
        self.ldap_client = Mock(_LDAPClient)
        self.ldap_factory = Mock(_LDAPFactory)
        self.ldap_factory.new_ldap_config.return_value = self.ldap_config
        self.ldap_factory.new_ldap_result_formatter.return_value = self.ldap_result_formatter
        self.ldap_factory.new_ldap_client.return_value = self.ldap_client
        self.ldap_plugin = LDAPPlugin()
        self.ldap_plugin.ldap_factory = self.ldap_factory

    def test_load(self):
        self.ldap_plugin.load(self.config)

        self.ldap_factory.new_ldap_config.assert_called_once_with(self.config['config'])
        self.ldap_factory.new_ldap_result_formatter.assert_called_once_with(self.ldap_config)
        self.ldap_factory.new_ldap_client.assert_called_once_with(self.ldap_config)
        self.ldap_client.set_up.assert_called_once_with()

    def test_unload(self):
        self.ldap_plugin.load(self.config)
        self.ldap_plugin.unload()

        self.ldap_client.close.assert_called_once_with()

    def test_search(self):
        term = u'foobar'
        self.ldap_config.build_search_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = sentinel.search_result
        self.ldap_result_formatter.format.return_value = sentinel.format_result

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.search(term)

        self.ldap_config.build_search_filter.assert_called_once_with(term.encode('UTF-8'))
        self.ldap_client.search.assert_called_once_with(sentinel.filter)
        self.ldap_result_formatter.format.assert_called_once_with(sentinel.search_result)
        self.assertIs(result, sentinel.format_result)

    def test_list_empty(self):
        uids = []
        self.ldap_config.build_list_filter.return_value = None
        self.ldap_client.search.side_effect = TypeError('must be string, not None')
        self.ldap_result_formatter.format.return_value = []

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.assertEquals(result, [])

    def test_list_with_uids(self):
        uids = ['123', '456']
        self.ldap_config.build_list_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = sentinel.search_result
        self.ldap_result_formatter.format.return_value = sentinel.format_result

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.ldap_config.build_list_filter.assert_called_once_with(uids)
        self.ldap_client.search.assert_called_once_with(sentinel.filter)
        self.ldap_result_formatter.format.assert_called_once_with(sentinel.search_result)
        self.assertIs(result, sentinel.format_result)

    def test_list_no_unique_column(self):
        uids = ['123', '456']
        self.ldap_config.unique_column.return_value = None

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.assertFalse(self.ldap_config.build_list_filter.called)
        self.assertEqual([], result)


class _TestLDAPFactory(unittest.TestCase):

    def setUp(self):
        self.ldap_factory = _LDAPFactory()

    def test_ldap_config(self):
        ldap_config = self.ldap_factory.new_ldap_config({})

        self.assertIsInstance(ldap_config, _LDAPConfig)

    def test_ldap_client(self):
        ldap_client = self.ldap_factory.new_ldap_client(sentinel.ldap_config)

        self.assertIsInstance(ldap_client, _LDAPClient)

    def test_ldap_result_formatter(self):
        ldap_result_formatter = self.ldap_factory.new_ldap_result_formatter(sentinel.ldap_config)

        self.assertIsInstance(ldap_result_formatter, _LDAPResultFormatter)


class TestLDAPConfig(unittest.TestCase):

    def test_name(self):
        value = 'foo'

        ldap_config = _LDAPConfig({'name': value})

        self.assertEqual(value, ldap_config.name())

    def test_name_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertRaises(Exception, ldap_config.name)

    def test_binary_uid_field_not_set(self):
        ldap_config = _LDAPConfig({})

        self.assertFalse(ldap_config.has_binary_uid())

    def test_has_binary_uid_field(self):
        ldap_config = _LDAPConfig({'binary_uid': True})

        self.assertTrue(ldap_config.has_binary_uid())

    def test_unique_column(self):
        value = 'entryUUID'

        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMN: value,
        })

        self.assertEqual(value, ldap_config.unique_column())

    def test_unique_column_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(None, ldap_config.unique_column())

    def test_format_columns(self):
        value = {'firstname': '{givenName}'}

        ldap_config = _LDAPConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: value,
        })

        self.assertEqual(value, ldap_config.format_columns())

    def test_format_columns_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(None, ldap_config.format_columns())

    def test_ldap_uri(self):
        value = 'ldap://example.org'

        ldap_config = _LDAPConfig({'ldap_uri': value})

        self.assertEqual(value, ldap_config.ldap_uri())

    def test_ldap_uri_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertRaises(Exception, ldap_config.ldap_uri)

    def test_ldap_base_dn(self):
        value = 'ou=people,dc=example,dc=org'

        ldap_config = _LDAPConfig({'ldap_base_dn': value})

        self.assertEqual(value, ldap_config.ldap_base_dn())

    def test_ldap_base_dn_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertRaises(Exception, ldap_config.ldap_base_dn)

    def test_ldap_username(self):
        value = 'john'

        ldap_config = _LDAPConfig({'ldap_username': value})

        self.assertEqual(value, ldap_config.ldap_username())

    def test_ldap_username_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_USERNAME, ldap_config.ldap_username())

    def test_ldap_password(self):
        value = 'foobar'

        ldap_config = _LDAPConfig({'ldap_password': value})

        self.assertEqual(value, ldap_config.ldap_password())

    def test_ldap_password_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_PASSWORD, ldap_config.ldap_password())

    def test_ldap_network_timeout(self):
        value = 4.0

        ldap_config = _LDAPConfig({'ldap_network_timeout': value})

        self.assertEqual(value, ldap_config.ldap_network_timeout())

    def test_ldap_network_timeout_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_NETWORK_TIMEOUT, ldap_config.ldap_network_timeout())

    def test_ldap_timeout(self):
        value = 42.0

        ldap_config = _LDAPConfig({'ldap_timeout': value})

        self.assertEqual(value, ldap_config.ldap_timeout())

    def test_ldap_timeout_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_TIMEOUT, ldap_config.ldap_timeout())

    def test_attributes_with_nothing(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(None, ldap_config.attributes())

    def test_attributes_with_unique_column_only_returns_none(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID'
        })

        self.assertEquals(None, ldap_config.attributes())

    def test_attributes_with_format_columns(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: {
                'firstname': '{givenName}',
                'lastname': '{sn}',
            },
        })

        assert_that(ldap_config.attributes(), contains_inanyorder('givenName', 'sn'))

    def test_attributes_with_unique_column_and_format_columns(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: {
                'firstname': '{givenName}',
                'lastname': '{sn}',
            },
            BaseSourcePlugin.UNIQUE_COLUMN: 'uid'
        })

        assert_that(ldap_config.attributes(), contains_inanyorder('givenName', 'sn', 'uid'))

    def test_attributes_with_unique_column_in_format_columns(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.FORMAT_COLUMNS: {
                'firstname': '{givenName}',
                'lastname': '{sn}',
            },
            BaseSourcePlugin.UNIQUE_COLUMN: 'sn'
        })

        assert_that(ldap_config.attributes(), contains_inanyorder('givenName', 'sn'))

    def test_build_search_filter_with_searched_columns_and_without_custom_filter(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SEARCHED_COLUMNS: ['cn'],
        })

        self.assertEqual('(cn=*foo*)', ldap_config.build_search_filter('foo'))

    def test_build_search_filter_with_searched_columns_and_with_custom_filter(self):
        ldap_config = _LDAPConfig({
            'ldap_custom_filter': '(cn=*%Q*)',
        })

        self.assertEqual('(cn=*foo*)', ldap_config.build_search_filter('foo'))

    def test_build_search_filter_without_searched_columns_and_with_custom_filter(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SEARCHED_COLUMNS: ['sn'],
            'ldap_custom_filter': '(cn=*%Q*)',
        })

        self.assertEqual('(cn=*foo*)', ldap_config.build_search_filter('foo'))

    def test_build_search_filter_without_searched_columns_and_without_custom_filter(self):
        ldap_config = _LDAPConfig({})

        self.assertRaises(Exception, ldap_config.build_search_filter, 'foo')

    def test_build_search_filter_searched_columns_escape_term(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SEARCHED_COLUMNS: ['cn'],
        })

        term = 'f)f'
        escaped_term = 'f\\29f'

        self.assertEqual('(cn=*%s*)' % escaped_term, ldap_config.build_search_filter(term))

    def test_build_search_filter_custom_filter_escape_term(self):
        ldap_config = _LDAPConfig({
            'ldap_custom_filter': '(cn=*%Q*)',
        })

        term = 'f)f'
        escaped_term = 'f\\29f'

        self.assertEqual('(cn=*%s*)' % escaped_term, ldap_config.build_search_filter(term))

    def test_build_search_filter_multiple_columns(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SEARCHED_COLUMNS: ['givenName', 'sn'],
        })

        term = 'foo'
        expected = '(|(givenName=*{term}*)(sn=*{term}*))'.format(term=term)

        self.assertEqual(expected, ldap_config.build_search_filter(term))

    def test_build_list_filter_no_item(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID',
        })
        uids = []

        self.assertFalse(ldap_config.build_list_filter(uids))

    def test_build_list_filter_one_item(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID',
        })
        uids = ['foo']

        self.assertEqual('(entryUUID=foo)', ldap_config.build_list_filter(uids))

    def test_build_list_filter_two_items(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID',
        })
        uids = ['foo', 'bar']

        self.assertEqual('(|(entryUUID=foo)(entryUUID=bar))', ldap_config.build_list_filter(uids))


class TestLDAPClient(unittest.TestCase):

    def setUp(self):
        self.uri = 'ldap://example.org'
        self.base_dn = 'ou=people,dc=foobar'
        self.attributes = ['entryUUID', 'givenName']
        self.username = 'cn=admin,dc=foobar'
        self.password = 'fol'
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.ldap_uri.return_value = self.uri
        self.ldap_config.ldap_base_dn.return_value = self.base_dn
        self.ldap_config.attributes.return_value = self.attributes
        self.ldap_config.ldap_username.return_value = self.username
        self.ldap_config.ldap_password.return_value = self.password
        self.ldap_obj = Mock(LDAPObject)
        self.ldap_obj_factory = Mock()
        self.ldap_obj_factory.return_value = self.ldap_obj
        self.ldap_client = _LDAPClient(self.ldap_config, self.ldap_obj_factory)

    def test_set_up(self):
        self.ldap_client.set_up()

        self.ldap_obj_factory.assert_called_once_with(self.uri)
        self.ldap_obj.simple_bind_s.assert_called_once_with(self.username, self.password)

    def test_set_up_when_already_set_up(self):
        self.ldap_client.set_up()
        self.ldap_client.set_up()

        self.ldap_obj_factory.assert_called_once_with(self.uri)

    def test_close(self):
        self.ldap_client.set_up()

        self.ldap_client.close()

        self.ldap_obj.unbind_s.assert_called_once_with()

    def test_close_when_already_closed(self):
        self.ldap_client.set_up()

        self.ldap_client.close()
        self.ldap_client.close()

        self.ldap_obj.unbind_s.assert_called_once_with()

    def test_search(self):
        self.ldap_obj.search_s.return_value = sentinel

        result = self.ldap_client.search('foo')

        self.ldap_obj.search_s.assert_called_once_with(self.base_dn, ANY, 'foo', self.attributes)
        self.assertEqual(1, self.ldap_obj_factory.call_count)
        self.assertIs(result, sentinel)

    def test_search_on_filter_error(self):
        self.ldap_obj.search_s.side_effect = ldap.FILTER_ERROR('moo')

        self.ldap_client.set_up()
        result = self.ldap_client.search('foo')

        self.assertEqual(result, [])
        self.assertEqual(1, self.ldap_obj_factory.call_count)
        self.assertEqual(1, self.ldap_obj.search_s.call_count)

    def test_search_on_server_down_error(self):
        self.ldap_obj.search_s.side_effect = ldap.SERVER_DOWN('moo')

        self.ldap_client.set_up()
        result = self.ldap_client.search('foo')

        self.assertEqual(result, [])
        self.assertEqual(2, self.ldap_obj_factory.call_count)
        self.assertEqual(2, self.ldap_obj.search_s.call_count)

    def test_multiple_search(self):
        self.ldap_client.search('foo')
        self.ldap_client.search('bar')
        self.ldap_client.search('foobar')

        self.assertEqual(1, self.ldap_obj.simple_bind_s.call_count)
        self.assertEqual(3, self.ldap_obj.search_s.call_count)


class TestLDAPResultFormatter(unittest.TestCase):

    def setUp(self):
        self.name = 'foo'
        self.unique_column = 'entryUUID'
        self.format_columns = {'firstname': '{givenName}'}
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.name.return_value = self.name
        self.ldap_config.unique_column.return_value = self.unique_column
        self.ldap_config.format_columns.return_value = self.format_columns
        self.ldap_result_formatter = _LDAPResultFormatter(self.ldap_config)
        self.SourceResult = make_result_class(self.name, self.unique_column, self.format_columns)

    def test_format(self):
        raw_results = [
            ('dn', {'entryUUID': ['0123'], 'givenName': ['John']}),
        ]
        expected_results = [
            self.SourceResult({'entryUUID': '0123', 'givenName': 'John'})
        ]

        results = self.ldap_result_formatter.format(raw_results)

        self.assertEqual(expected_results, results)
