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

from ldap.ldapobject import LDAPObject
from mock import Mock, ANY
from xivo_dird.plugins.base_plugins import BaseSourcePlugin
from xivo_dird.plugins.ldap_plugin import _LDAPConfig, \
    _LDAPResultFormatter, _LDAPClient
from xivo_dird.plugins.source_result import make_result_class


class TestLDAPConfig(unittest.TestCase):

    def test_name(self):
        value = 'foo'

        ldap_config = _LDAPConfig({'name': value})

        self.assertEqual(value, ldap_config.name())

    def test_name_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertRaises(Exception, ldap_config.name)

    def test_unique_columns(self):
        value = ['entryUUID']

        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: value,
        })

        self.assertEqual(value, ldap_config.unique_columns())

    def test_unique_columns_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(None, ldap_config.unique_columns())

    def test_source_to_display(self):
        value = {'givenName': 'firstname'}

        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SOURCE_TO_DISPLAY: value,
        })

        self.assertEqual(value, ldap_config.source_to_display())

    def test_source_to_display_when_absent(self):
        ldap_config = _LDAPConfig({})

        self.assertEqual(None, ldap_config.source_to_display())

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

    def test_attributes_with_unique_columns_only_returns_none(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: ['entryUUID']
        })

        self.assertEquals(None, ldap_config.attributes())

    def test_attributes_with_source_to_display(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SOURCE_TO_DISPLAY: {
                'givenName': 'firstname',
                'sn': 'lastname',
            },
        })

        self.assertEqual(['givenName', 'sn'], ldap_config.attributes())

    def test_attributes_with_unique_columns_and_source_to_display(self):
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.SOURCE_TO_DISPLAY: {
                'givenName': 'firstname',
                'sn': 'lastname',
            },
            BaseSourcePlugin.UNIQUE_COLUMNS: [
                'uid',
                'sn',
            ],
        })

        self.assertEqual(['givenName', 'sn', 'uid'], ldap_config.attributes())

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
        columns = ['entryUUID']
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: columns,
        })
        uids = []

        self.assertFalse(ldap_config.build_list_filter(uids))

    def test_build_list_filter_one_item(self):
        columns = ['entryUUID']
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: columns,
        })
        uids = [('foo',)]

        self.assertEqual('(entryUUID=foo)', ldap_config.build_list_filter(uids))

    def test_build_list_filter_two_items(self):
        columns = ['entryUUID']
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: columns,
        })
        uids = [('foo',), ('bar',)]

        self.assertEqual('(|(entryUUID=foo)(entryUUID=bar))', ldap_config.build_list_filter(uids))

    def test_build_list_filter_one_multi_column_item(self):
        columns = ['uid', 'sn']
        ldap_config = _LDAPConfig({
            BaseSourcePlugin.UNIQUE_COLUMNS: columns,
        })
        uids = [('bar', 'foo',)]

        self.assertEqual('(&(uid=bar)(sn=foo))', ldap_config.build_list_filter(uids))


class TestLDAPClient(unittest.TestCase):

    def setUp(self):
        self.base_dn = 'ou=people,dc=foobar'
        self.attributes = ['entryUUID', 'givenName']
        self.username = 'cn=admin,dc=foobar'
        self.password = 'fol'
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.ldap_base_dn.return_value = self.base_dn
        self.ldap_config.attributes.return_value = self.attributes
        self.ldap_config.ldap_username.return_value = self.username
        self.ldap_config.ldap_password.return_value = self.password
        self.ldap_obj = Mock(LDAPObject)
        self.ldap_client = _LDAPClient(self.ldap_config, self.ldap_obj)

    def test_bind(self):
        self.ldap_client.bind()

        self.ldap_obj.simple_bind_s.assert_called_once_with(self.username, self.password)

    def test_unbind(self):
        self.ldap_client.unbind()

        self.ldap_obj.unbind_s.assert_called_once_with()

    def test_search(self):
        self.ldap_client.search('foo')

        self.ldap_obj.search_s.assert_called_once_with(self.base_dn, ANY, 'foo', self.attributes)


class TestLDAPResultFormatter(unittest.TestCase):

    def setUp(self):
        self.name = 'foo'
        self.unique_columns = ['entryUUID']
        self.source_to_display = {'givenName': 'firstname'}
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.name.return_value = self.name
        self.ldap_config.unique_columns.return_value = self.unique_columns
        self.ldap_config.source_to_display.return_value = self.source_to_display
        self.ldap_result_formatter = _LDAPResultFormatter(self.ldap_config)
        self.SourceResult = make_result_class(self.name, self.unique_columns, self.source_to_display)

    def test_format(self):
        raw_results = [
            ('dn', {'entryUUID': ['0123'], 'givenName': ['John']}),
        ]
        expected_results = [
            self.SourceResult({'entryUUID': '0123', 'givenName': 'John'})
        ]

        results = self.ldap_result_formatter.format(raw_results)

        self.assertEqual(expected_results, results)
