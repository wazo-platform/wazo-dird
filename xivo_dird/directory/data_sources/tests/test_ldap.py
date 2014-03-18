# -*- coding: utf-8 -*-

# Copyright (C) 2007-2014 Avencall
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

import unittest
from mock import Mock, patch
from xivo_dird.directory.data_sources.ldap import LDAPDirectoryDataSource


class TestLDAPDirectoryDataSource(unittest.TestCase):

    def setUp(self):
        self._ldap = LDAPDirectoryDataSource(None, None)

    def test_decode_results(self):
        ldap_results = [('dn=someóne,dn=somewhere', {'cn': ['anó nymous'],
                                                      'sn': ['nymous']}),
                        ('dn=somebódy,dn=someplace', {'cn': ['jóhn doe'],
                                                       'sn': ['dóe']})]
        expected_result = [(u'dn=someóne,dn=somewhere', {u'cn': [u'anó nymous'],
                                                          u'sn': [u'nymous']}),
                           (u'dn=somebódy,dn=someplace', {u'cn': [u'jóhn doe'],
                                                           u'sn': [u'dóe']})]
        decode_entry = Mock()
        returns = iter(expected_result)
        decode_entry.side_effect = lambda index: returns.next()
        self._ldap._decode_entry = decode_entry

        result = self._ldap._decode_results(ldap_results)

        self.assertEquals(result, expected_result)
        decode_entry.assert_was_called_with(ldap_results[0])
        decode_entry.assert_was_called_with(ldap_results[1])

    def test_decode_entry(self):
        entry = ('dn=someóne,dn=somewhere', {'cn': ['anó nymous'],
                                              'sn': ['nymous']})
        expected_result = (u'dn=someóne,dn=somewhere', {u'cn': [u'anó nymous'],
                                                         u'sn': [u'nymous']})
        decode_attributes = Mock()
        decode_attributes.return_value = expected_result[1]
        self._ldap._decode_attributes = decode_attributes

        result = self._ldap._decode_entry(entry)

        self.assertEqual(result, expected_result)
        decode_attributes.assert_called_once_with(entry[1])

    def test_decode_attributes(self):
        attributes = {'cn': ['anó nymous'],
                      'sn': ['nymous']}
        expected_result = {u'cn': [u'anó nymous'],
                           u'sn': [u'nymous']}

        decode_values = Mock()
        returns = iter(expected_result.values())
        decode_values.side_effect = lambda index: returns.next()
        self._ldap._decode_values = decode_values

        result = self._ldap._decode_attributes(attributes)

        self.assertEqual(result, expected_result)
        decode_values.assert_was_called_with(attributes['cn'])
        decode_values.assert_was_called_with(attributes['sn'])

    def test_decode_values(self):
        values = ['anó nymous']
        expected_result = [u'anó nymous']

        result = self._ldap._decode_values(values)

        self.assertEqual(result, expected_result)

    @patch('xivo_dao.ldap_dao.build_ldapinfo_from_ldapfilter')
    def test_get_ldap_config(self, build_ldapinfo_from_ldapfilter):
        uri = "ldapfilter://filtername"
        ldapinfo = build_ldapinfo_from_ldapfilter.return_value = Mock()

        result = LDAPDirectoryDataSource._get_ldap_config(uri)

        self.assertEqual(result, ldapinfo)
        build_ldapinfo_from_ldapfilter.assert_called_once_with("filtername")

    @patch('xivo_dird.directory.data_sources.ldap.XivoLDAP')
    def test_try_connect(self, XivoLDAP):
        ldap_config = Mock()
        directory = LDAPDirectoryDataSource(ldap_config, None)

        directory._try_connect()

        XivoLDAP.assert_called_once_with(ldap_config)

    @patch.object(LDAPDirectoryDataSource, '_get_ldap_config')
    @patch.object(LDAPDirectoryDataSource, '_get_key_mapping')
    @patch('xivo_dird.directory.data_sources.ldap.LDAPDirectoryDataSource.__init__')
    def test_new_from_contents(self, constructor, get_key_mapping, get_ldap_config):
        key_mapping = get_key_mapping.return_value = Mock()
        ldap_config = get_ldap_config.return_value = Mock()
        constructor.return_value = None

        contents = {
            'uri': 'ldapfilter://filtername',
        }

        LDAPDirectoryDataSource.new_from_contents(contents)

        get_key_mapping.assert_called_once_with(contents)
        get_ldap_config.assert_called_once_with(contents['uri'])
        constructor.assert_called_once_with(ldap_config, key_mapping)
