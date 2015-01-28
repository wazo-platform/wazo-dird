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

import ldap
import time

from .base_dird_integration_test import BaseDirdIntegrationTest

from collections import namedtuple
from ldap.modlist import addModlist
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import empty


Contact = namedtuple('Contact', ['firstname', 'lastname', 'number'])

class LDAPHelper(object):

    LDAP_URI = 'ldap://localhost:3389'

    BASE_DN = 'dc=xivo-dird,dc=xivo,dc=io'
    ADMIN_DN = 'cn=admin,{}'.format(BASE_DN)
    ADMIN_PASSWORD = 'xivopassword'
    PEOPLE_DN = 'ou=people,{}'.format(BASE_DN)

    def __init__(self):
        self._ldap_obj = ldap.initialize(self.LDAP_URI)
        self._ldap_obj.simple_bind_s(self.ADMIN_DN, self.ADMIN_PASSWORD)

    def add_ou_people(self):
        modlist = addModlist({
            'objectClass': ['organizationalUnit'],
            'ou': ['people'],
        })

        self._ldap_obj.add_s(self.PEOPLE_DN, modlist)

    def add_contact(self, contact):
        cn = '{} {}'.format(contact.firstname, contact.lastname)
        dn = 'cn={},{}'.format(cn, self.PEOPLE_DN)
        modlist = addModlist({
            'objectClass': ['inetOrgPerson'],
            'cn': [cn],
            'givenName': [contact.firstname],
            'sn': [contact.lastname],
            'telephoneNumber': [contact.number],
        })

        self._ldap_obj.add_s(dn, modlist)


def add_contacts(contacts):
    for _ in xrange(5):
        try:
            helper = LDAPHelper()
            break
        except ldap.SERVER_DOWN:
            time.sleep(1)
    else:
        raise Exception('could not add contacts: LDAP server is down')

    helper.add_ou_people()
    for contact in contacts:
        helper.add_contact(contact)


class TestLDAP(BaseDirdIntegrationTest):

    asset = 'ldap'

    CONTACTS = [
        Contact('Alice', 'Wonderland', '1001'),
        Contact('Bob', 'Barker', '1002'),
    ]

    @classmethod
    def setUpClass(cls):
        super(TestLDAP, cls).setUpClass()

        try:
            add_contacts(cls.CONTACTS)
        except Exception:
            super(TestLDAP, cls).tearDownClass()
            raise

    def test_lookup_on_cn(self):
        result = self.lookup('Ali', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'Wonderland', '1001'))

    def test_lookup_on_telephone_number(self):
        result = self.lookup('1001', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'Wonderland', '1001'))

    def test_no_result(self):
        result = self.lookup('frack', 'default')

        assert_that(result['results'], empty())
