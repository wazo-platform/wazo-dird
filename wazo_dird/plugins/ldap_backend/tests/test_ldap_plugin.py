# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
import uuid
from unittest.mock import ANY, Mock, call, sentinel

import ldap
from hamcrest import assert_that, contains_inanyorder
from ldap.ldapobject import LDAPObject

from wazo_dird.plugins.base_plugins import BaseSourcePlugin
from wazo_dird.plugins.source_result import make_result_class

from ..plugin import (
    LDAPPlugin,
    _LDAPClient,
    _LDAPConfig,
    _LDAPFactory,
    _LDAPResultFormatter,
)


class TestLDAPPlugin(unittest.TestCase):
    def setUp(self):
        self.config = {'config': sentinel}
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_result_formatter = Mock(_LDAPResultFormatter)
        self.ldap_client = Mock(_LDAPClient)
        self.ldap_factory = Mock(_LDAPFactory)
        self.ldap_factory.new_ldap_config.return_value = self.ldap_config
        self.ldap_factory.new_ldap_result_formatter.return_value = (
            self.ldap_result_formatter
        )
        self.ldap_factory.new_ldap_client.return_value = self.ldap_client
        self.ldap_plugin = LDAPPlugin()
        self.ldap_plugin.ldap_factory = self.ldap_factory

    def test_load(self):
        self.ldap_plugin.load(self.config)

        self.ldap_factory.new_ldap_config.assert_called_once_with(self.config['config'])
        self.ldap_factory.new_ldap_result_formatter.assert_called_once_with(
            self.ldap_config
        )
        self.ldap_factory.new_ldap_client.assert_called_once_with(self.ldap_config)
        self.ldap_client.set_up.assert_called_once_with()

    def test_unload(self):
        self.ldap_plugin.load(self.config)
        self.ldap_plugin.unload()

        self.ldap_client.close.assert_called_once_with()

    def test_search(self):
        term = 'foobar'
        self.ldap_config.build_search_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = sentinel.search_result
        self.ldap_result_formatter.format.return_value = sentinel.format_result

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.search(term)

        self.ldap_config.build_search_filter.assert_called_once_with(term)
        self.ldap_client.search.assert_called_once_with(sentinel.filter)
        self.ldap_result_formatter.format.assert_called_once_with(
            sentinel.search_result
        )
        self.assertIs(result, sentinel.format_result)

    def test_first_match(self):
        exten = '123456'
        self.ldap_config.build_first_match_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = [
            (sentinel.result_1_dn, sentinel.result_1_attrs),
            sentinel.result_2,
        ]
        self.ldap_result_formatter.format_one_result.return_value = (
            sentinel.format_result
        )

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.first_match(exten)

        self.ldap_config.build_first_match_filter.assert_called_once_with(exten)
        self.ldap_client.search.assert_called_once_with(sentinel.filter, 1)
        self.ldap_result_formatter.format_one_result.assert_called_once_with(
            sentinel.result_1_attrs
        )
        self.assertIs(result, sentinel.format_result)

    def test_first_match_return_none_when_no_match(self):
        exten = '123456'
        self.ldap_config.build_first_match_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = []

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.first_match(exten)

        self.ldap_config.build_first_match_filter.assert_called_once_with(exten)
        self.ldap_client.search.assert_called_once_with(sentinel.filter, 1)
        self.assertIs(result, None)

    def test_match_all(self):
        extens = ['123', '456']
        self.ldap_config.first_matched_columns.return_value = ['column1', 'column2']
        self.ldap_config.build_match_all_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = [
            (sentinel.result_1_dn, sentinel.result_1_attrs),
            (sentinel.result_2_dn, sentinel.result_2_attrs),
            (None, sentinel.result_3_attrs),
        ]
        format_result = Mock(fields={'column1': '123', 'column2': '456'})
        self.ldap_result_formatter.format_one_result.return_value = format_result

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.match_all(extens)

        self.ldap_config.build_match_all_filter.assert_called_once_with(extens)
        self.ldap_client.search.assert_called_once_with(sentinel.filter)
        calls = [call(sentinel.result_1_attrs), call(sentinel.result_2_attrs)]
        self.ldap_result_formatter.format_one_result.assert_has_calls(calls)
        self.assertEqual(result, {'123': format_result, '456': format_result})

    def test_list_empty(self):
        uids = []
        self.ldap_config.build_list_filter.return_value = None
        self.ldap_client.search.side_effect = TypeError('must be string, not None')
        self.ldap_result_formatter.format.return_value = []

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.assertEqual(result, [])

    def test_list_with_uids(self):
        uids = ['123', '456']
        self.ldap_config.build_list_filter.return_value = sentinel.filter
        self.ldap_client.search.return_value = sentinel.search_result
        self.ldap_result_formatter.format.return_value = sentinel.format_result

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.ldap_config.build_list_filter.assert_called_once_with(uids)
        self.ldap_client.search.assert_called_once_with(sentinel.filter)
        self.ldap_result_formatter.format.assert_called_once_with(
            sentinel.search_result
        )
        self.assertIs(result, sentinel.format_result)

    def test_list_no_unique_column(self):
        uids = ['123', '456']
        self.ldap_config.unique_column.return_value = None

        self.ldap_plugin.load(self.config)
        result = self.ldap_plugin.list(uids)

        self.assertFalse(self.ldap_config.build_list_filter.called)
        self.assertEqual([], result)


class TestLDAPFactory(unittest.TestCase):
    def setUp(self):
        self.ldap_factory = _LDAPFactory()

    def test_ldap_config(self):
        minimal_config = {'ldap_custom_filter': 'filter'}
        ldap_config = self.ldap_factory.new_ldap_config(minimal_config)

        self.assertIsInstance(ldap_config, _LDAPConfig)

    def test_ldap_client(self):
        ldap_config = Mock()
        ldap_client = self.ldap_factory.new_ldap_client(ldap_config)

        self.assertIsInstance(ldap_client, _LDAPClient)

    def test_ldap_result_formatter(self):
        ldap_config = Mock()
        ldap_result_formatter = self.ldap_factory.new_ldap_result_formatter(ldap_config)

        self.assertIsInstance(ldap_result_formatter, _LDAPResultFormatter)


class TestLDAPConfig(unittest.TestCase):
    def new_ldap_config(self, config):
        config.update({BaseSourcePlugin.SEARCHED_COLUMNS: ['cn']})
        return _LDAPConfig(config)

    def test_that_a_config_without_searched_columns_or_filter_raises(self):
        self.assertRaises(LookupError, _LDAPConfig, {})

    def test_name(self):
        value = 'foo'

        ldap_config = self.new_ldap_config({'name': value})

        self.assertEqual(value, ldap_config.name())

    def test_name_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertRaises(Exception, ldap_config.name)

    def test_unique_column_format_field_not_set(self):
        ldap_config = self.new_ldap_config({})

        self.assertFalse(ldap_config.has_binary_uuid())

    def test_unique_column_format_binary_uuid(self):
        ldap_config = self.new_ldap_config({'unique_column_format': 'binary_uuid'})

        self.assertTrue(ldap_config.has_binary_uuid())

    def test_unique_column(self):
        value = 'entryUUID'

        ldap_config = self.new_ldap_config({BaseSourcePlugin.UNIQUE_COLUMN: value})

        self.assertEqual(value, ldap_config.unique_column())

    def test_unique_column_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(None, ldap_config.unique_column())

    def test_format_columns(self):
        value = {'firstname': '{givenName}'}

        ldap_config = self.new_ldap_config({BaseSourcePlugin.FORMAT_COLUMNS: value})

        self.assertEqual(value, ldap_config.format_columns())

    def test_format_columns_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(None, ldap_config.format_columns())

    def test_ldap_uri(self):
        value = 'ldap://example.org'

        ldap_config = self.new_ldap_config({'ldap_uri': value})

        self.assertEqual(value, ldap_config.ldap_uri())

    def test_ldap_uri_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertRaises(Exception, ldap_config.ldap_uri)

    def test_ldap_base_dn(self):
        value = 'ou=people,dc=example,dc=org'

        ldap_config = self.new_ldap_config({'ldap_base_dn': value})

        self.assertEqual(value, ldap_config.ldap_base_dn())

    def test_ldap_base_dn_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertRaises(Exception, ldap_config.ldap_base_dn)

    def test_ldap_username(self):
        value = 'john'

        ldap_config = self.new_ldap_config({'ldap_username': value})

        self.assertEqual(value, ldap_config.ldap_username())

    def test_ldap_username_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_USERNAME, ldap_config.ldap_username())

    def test_ldap_password(self):
        value = 'foobar'

        ldap_config = self.new_ldap_config({'ldap_password': value})

        self.assertEqual(value, ldap_config.ldap_password())

    def test_ldap_password_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_PASSWORD, ldap_config.ldap_password())

    def test_ldap_network_timeout(self):
        value = 4.0

        ldap_config = self.new_ldap_config({'ldap_network_timeout': value})

        self.assertEqual(value, ldap_config.ldap_network_timeout())

    def test_ldap_network_timeout_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(
            _LDAPConfig.DEFAULT_LDAP_NETWORK_TIMEOUT, ldap_config.ldap_network_timeout()
        )

    def test_ldap_timeout(self):
        value = 42.0

        ldap_config = self.new_ldap_config({'ldap_timeout': value})

        self.assertEqual(value, ldap_config.ldap_timeout())

    def test_ldap_timeout_when_absent(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(_LDAPConfig.DEFAULT_LDAP_TIMEOUT, ldap_config.ldap_timeout())

    def test_attributes_with_nothing(self):
        ldap_config = self.new_ldap_config({})

        self.assertEqual(None, ldap_config.attributes())

    def test_attributes_with_unique_column_only_returns_none(self):
        ldap_config = self.new_ldap_config(
            {BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID'}
        )

        self.assertEqual(None, ldap_config.attributes())

    def test_attributes_with_format_columns(self):
        ldap_config = self.new_ldap_config(
            {
                BaseSourcePlugin.FORMAT_COLUMNS: {
                    'firstname': '{givenName}',
                    'lastname': '{sn}',
                }
            }
        )

        assert_that(ldap_config.attributes(), contains_inanyorder('givenName', 'sn'))

    def test_attributes_with_unique_column_and_format_columns(self):
        ldap_config = self.new_ldap_config(
            {
                BaseSourcePlugin.FORMAT_COLUMNS: {
                    'firstname': '{givenName}',
                    'lastname': '{sn}',
                },
                BaseSourcePlugin.UNIQUE_COLUMN: 'uid',
            }
        )

        assert_that(
            ldap_config.attributes(), contains_inanyorder('givenName', 'sn', 'uid')
        )

    def test_attributes_with_unique_column_in_format_columns(self):
        ldap_config = self.new_ldap_config(
            {
                BaseSourcePlugin.FORMAT_COLUMNS: {
                    'firstname': '{givenName}',
                    'lastname': '{sn}',
                },
                BaseSourcePlugin.UNIQUE_COLUMN: 'sn',
            }
        )

        assert_that(ldap_config.attributes(), contains_inanyorder('givenName', 'sn'))

    def test_build_search_filter_with_searched_columns_and_without_custom_filter(self):
        ldap_config = _LDAPConfig({BaseSourcePlugin.SEARCHED_COLUMNS: ['cn']})

        self.assertEqual('(cn=*foo*)', ldap_config.build_search_filter('foo'))

    def test_build_search_filter_without_searched_columns_and_with_custom_filter(self):
        ldap_config = _LDAPConfig({'ldap_custom_filter': '(cn=*%Q*)'})

        self.assertEqual('(cn=*foo*)', ldap_config.build_search_filter('foo'))

    def test_build_search_filter_with_searched_columns_and_custom_filter(self):
        ldap_config = _LDAPConfig(
            {
                BaseSourcePlugin.SEARCHED_COLUMNS: ['sn'],
                'ldap_custom_filter': '(cn=*%Q*)',
            }
        )

        self.assertEqual(
            '(&(cn=*foo*)(sn=*foo*))', ldap_config.build_search_filter('foo')
        )

    def test_build_search_filter_with_searched_columns_and_custom_filter_unicode_term(
        self,
    ):
        ldap_config = _LDAPConfig(
            {
                BaseSourcePlugin.SEARCHED_COLUMNS: ['sn'],
                'ldap_custom_filter': '(cn=*%Q*)',
            }
        )

        self.assertEqual(
            '(&(cn=*Québec*)(sn=*Québec*))', ldap_config.build_search_filter('Québec')
        )

    def test_build_search_filter_searched_columns_escape_term(self):
        ldap_config = _LDAPConfig({BaseSourcePlugin.SEARCHED_COLUMNS: ['cn']})

        term = 'f)f'
        escaped_term = 'f\\29f'

        self.assertEqual(
            '(cn=*%s*)' % escaped_term, ldap_config.build_search_filter(term)
        )

    def test_build_search_filter_custom_filter_escape_term(self):
        ldap_config = _LDAPConfig({'ldap_custom_filter': '(cn=*%Q*)'})

        term = 'f)f'
        escaped_term = 'f\\29f'

        self.assertEqual(
            '(cn=*%s*)' % escaped_term, ldap_config.build_search_filter(term)
        )

    def test_build_search_filter_multiple_columns(self):
        ldap_config = _LDAPConfig(
            {BaseSourcePlugin.SEARCHED_COLUMNS: ['givenName', 'sn']}
        )

        term = 'foo'
        expected = '(|(givenName=*{term}*)(sn=*{term}*))'.format(term=term)

        self.assertEqual(expected, ldap_config.build_search_filter(term))

    def test_build_list_filter_no_item(self):
        ldap_config = self.new_ldap_config(
            {BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID'}
        )
        uids = []

        self.assertFalse(ldap_config.build_list_filter(uids))

    def test_build_list_filter_one_item(self):
        ldap_config = self.new_ldap_config(
            {BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID'}
        )
        uids = ['foo']

        self.assertEqual('(entryUUID=foo)', ldap_config.build_list_filter(uids))

    def test_build_list_filter_binary(self):
        uuid = 'f3bc2a27-7f38-4e30-adf5-873fe5ac484f'
        binary_uuid = '\\f3\\bc\\2a\\27\\7f\\38\\4e\\30\\ad\\f5\\87\\3f\\e5\\ac\\48\\4f'
        ldap_config = self.new_ldap_config(
            {
                BaseSourcePlugin.UNIQUE_COLUMN: 'objectGUID',
                'unique_column_format': 'binary_uuid',
            }
        )
        uids = [uuid]

        self.assertEqual(
            '(objectGUID=%s)' % binary_uuid, ldap_config.build_list_filter(uids)
        )

    def test_build_list_filter_two_items(self):
        ldap_config = self.new_ldap_config(
            {BaseSourcePlugin.UNIQUE_COLUMN: 'entryUUID'}
        )
        uids = ['foo', 'bar']

        self.assertEqual(
            '(|(entryUUID=foo)(entryUUID=bar))', ldap_config.build_list_filter(uids)
        )

    def test_build_match_all_filter_when_no_first_match_columns_filter(self):
        ldap_config = self.new_ldap_config({BaseSourcePlugin.FIRST_MATCHED_COLUMNS: []})

        self.assertEqual('(|)', ldap_config.build_match_all_filter(['1234']))


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
        self.ldap_obj.simple_bind_s.assert_called_once_with(
            self.username, self.password
        )

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
        self.ldap_obj.search_ext_s.return_value = sentinel

        result = self.ldap_client.search('foo')

        self.ldap_obj.search_ext_s.assert_called_once_with(
            self.base_dn, ANY, 'foo', self.attributes, sizelimit=-1
        )
        self.assertEqual(1, self.ldap_obj_factory.call_count)
        self.assertIs(result, sentinel)

    def test_search_on_filter_error(self):
        self.ldap_obj.search_ext_s.side_effect = ldap.FILTER_ERROR('moo')

        self.ldap_client.set_up()
        result = self.ldap_client.search('foo')

        self.assertEqual(result, [])
        self.assertEqual(1, self.ldap_obj_factory.call_count)
        self.assertEqual(1, self.ldap_obj.search_ext_s.call_count)

    def test_search_on_server_down_error(self):
        self.ldap_obj.search_ext_s.side_effect = ldap.SERVER_DOWN('moo')

        self.ldap_client.set_up()
        result = self.ldap_client.search('foo')

        self.assertEqual(result, [])
        self.assertEqual(2, self.ldap_obj_factory.call_count)
        self.assertEqual(2, self.ldap_obj.search_ext_s.call_count)

    def test_multiple_search(self):
        self.ldap_client.search('foo')
        self.ldap_client.search('bar')
        self.ldap_client.search('foobar')

        self.assertEqual(1, self.ldap_obj.simple_bind_s.call_count)
        self.assertEqual(3, self.ldap_obj.search_ext_s.call_count)


class TestLDAPResultFormatter(unittest.TestCase):
    def setUp(self):
        self.name = 'foo'
        self.unique_column = 'entryUUID'
        self.format_columns = {'firstname': '{givenName}'}
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.name.return_value = self.name
        self.ldap_config.unique_column.return_value = self.unique_column
        self.ldap_config.format_columns.return_value = self.format_columns
        self.SourceResult = make_result_class(
            'ldap', self.name, self.unique_column, self.format_columns
        )

    def test_format(self):
        formatter = self._new_formatter(has_binary_uuid=False)

        raw_results = [
            ('dn', {'entryUUID': [b'0123'], 'givenName': [b'Gr\xc3\xa9goire']})
        ]
        expected_results = [
            self.SourceResult({'entryUUID': '0123', 'givenName': 'Grégoire'})
        ]

        results = formatter.format(raw_results)

        self.assertEqual(expected_results, results)

    def test_format_with_binary_uid(self):
        formatter = self._new_formatter(has_binary_uuid=True)

        binary_uuid = os.urandom(16)
        encoded_uid = str(uuid.UUID(bytes=binary_uuid))

        raw_results = [('dn', {'entryUUID': [binary_uuid], 'givenName': [b'John']})]
        expected_results = [
            self.SourceResult({'entryUUID': encoded_uid, 'givenName': 'John'})
        ]

        results = formatter.format(raw_results)

        self.assertEqual(expected_results, results)

    def test_format_with_referals(self):
        formatter = self._new_formatter(has_binary_uuid=False)

        raw_results = [
            ('dn', {'entryUUID': [b'0123'], 'givenName': [b'John']}),
            (
                None,
                ['ldap://b.example.com/cn=test,dc=lan-quebec,dc=avencall,dc=com??sub'],
            ),
        ]
        expected_results = [
            self.SourceResult({'entryUUID': '0123', 'givenName': 'John'})
        ]

        results = formatter.format(raw_results)

        self.assertEqual(expected_results, results)

    def test_format_one_result(self):
        formatter = self._new_formatter(has_binary_uuid=False)

        raw_result = ('dn', {'entryUUID': [b'0123'], 'givenName': [b'Gr\xc3\xa9goire']})
        expected_result = self.SourceResult(
            {'entryUUID': '0123', 'givenName': 'Grégoire'}
        )

        dn, attrs = raw_result
        result = formatter.format_one_result(attrs)

        self.assertEqual(expected_result, result)

    def _new_formatter(self, has_binary_uuid):
        self.ldap_config.has_binary_uuid.return_value = has_binary_uuid
        return _LDAPResultFormatter(self.ldap_config)
