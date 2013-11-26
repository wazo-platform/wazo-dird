# -*- coding: utf-8 -*-

# Copyright (C) 2013 Avencall
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
import ldap
from mock import Mock, patch
from xivo_dird.ldap import XivoLDAP


class TestXivoLDAP(unittest.TestCase):

    @patch('ldap.initialize')
    def test_xivo_ldap_init(self, ldap_initialize):
        ldapobj = ldap_initialize.return_value = Mock()

        config = {
            'uri': 'ldap://host:389',
            'basedn': 'cn=User,dc=example,dc=com',
            'filter': 'sn=*',
            'username': 'username',
            'password': 'password',
        }

        xivo_ldap = XivoLDAP(config)

        self.assertEquals(xivo_ldap.dbname, config['basedn'])
        self.assertEquals(xivo_ldap.base_filter, config['filter'])
        self.assertEquals(xivo_ldap.base_attributes, None)
        self.assertEquals(xivo_ldap.base_scope, None)
        self.assertEquals(xivo_ldap.base_extensions, None)

        ldap_initialize.assert_called_once_with(config['uri'], 0)
        ldapobj.set_option.assert_any_call(ldap.OPT_REFERRALS, 0)
        ldapobj.set_option.assert_any_call(ldap.OPT_NETWORK_TIMEOUT, 0.1)
        ldapobj.set_option.assert_any_call(ldap.OPT_TIMEOUT, 1)
        ldapobj.simple_bind_s.assert_called_once_with('username', 'password')
