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
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import equal_to
from hamcrest import has_entry

Contact = namedtuple('Contact', ['firstname', 'lastname', 'number', 'city'])


class LDAPHelper(object):

    LDAP_URI = 'ldap://localhost:3899'

    BASE_DN = 'dc=xivo-dird,dc=xivo,dc=io'
    ADMIN_DN = 'cn=admin,{}'.format(BASE_DN)
    ADMIN_PASSWORD = 'xivopassword'
    QUEBEC_DN = 'ou=québec,{}'.format(BASE_DN)

    def __init__(self):
        self._ldap_obj = ldap.initialize(self.LDAP_URI)
        self._ldap_obj.simple_bind_s(self.ADMIN_DN, self.ADMIN_PASSWORD)

    def add_ou_quebec(self):
        modlist = addModlist({
            'objectClass': ['organizationalUnit'],
            'ou': ['quebec'],
        })

        self._ldap_obj.add_s(self.QUEBEC_DN, modlist)

    def add_contact(self, contact):
        cn = '{} {}'.format(contact.firstname, contact.lastname)
        dn = 'cn={},{}'.format(cn, self.QUEBEC_DN)
        modlist = addModlist({
            'objectClass': ['inetOrgPerson'],
            'cn': [cn],
            'givenName': [contact.firstname],
            'sn': [contact.lastname],
            'telephoneNumber': [contact.number],
            'l': [contact.city],
        })

        self._ldap_obj.add_s(dn, modlist)
        search_dn, result = self._ldap_obj.search_s(dn, ldap.SCOPE_BASE, attrlist=['entryUUID'])[0]
        return result['entryUUID'][0]


def add_contacts(contacts):
    for _ in xrange(10):
        try:
            helper = LDAPHelper()
            break
        except ldap.SERVER_DOWN:
            time.sleep(1)
    else:
        raise Exception('could not add contacts: LDAP server is down')

    entry_uuids = []
    helper.add_ou_quebec()
    for contact in contacts:
        entry_uuid = helper.add_contact(contact)
        entry_uuids.append(entry_uuid)

    return entry_uuids


class TestLDAP(BaseDirdIntegrationTest):

    asset = 'ldap'

    CONTACTS = [
        Contact('Alice', 'Wonderland', '1001', 'Lyon'),
        Contact('Bob', 'Barker', '1002', 'Lyon'),
        Contact('Connor', 'Manson', '1003', 'QC'),
        Contact('François', 'Hollande', '1004', 'QC'),
    ]
    entry_uuids = []

    @classmethod
    def setUpClass(cls):
        super(TestLDAP, cls).setUpClass()

        try:
            cls.entry_uuids = add_contacts(cls.CONTACTS)
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

    def test_lookup_with_non_ascii_characters(self):
        result = self.lookup(u'ç', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains(u'François', 'Hollande', '1004'))

    def test_reverse_lookup(self):
        result = self.reverse('1001', 'default')

        assert_that(result['display'], equal_to('Alice Wonderland'))

    def test_no_result(self):
        result = self.lookup('frack', 'default')

        assert_that(result['results'], empty())

    def test_ldap_favorites(self):
        self.put_favorite('test_ldap', self.entry_uuids[0])
        self.put_favorite('test_ldap', self.entry_uuids[2])

        result = self.favorites('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', 'Wonderland', '1001')),
            has_entry('column_values', contains('Connor', 'Manson', '1003'))))


class TestLDAPWithCustomFilter(BaseDirdIntegrationTest):

    asset = 'ldap_city'

    CONTACTS = [
        Contact('Alice', 'Wonderland', '1001', 'Lyon'),
        Contact('Bob', 'Barker', '1002', 'Québec'),
        Contact('Charlé', 'Doe', '1003', 'Québec'),
    ]
    entry_uuids = []

    @classmethod
    def setUpClass(cls):
        super(TestLDAPWithCustomFilter, cls).setUpClass()

        try:
            cls.entry_uuids = add_contacts(cls.CONTACTS)
        except Exception:
            super(TestLDAPWithCustomFilter, cls).tearDownClass()
            raise

    def test_lookup_on_cn(self):
        result = self.lookup(u'charlé', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains(u'Charlé', 'Doe', '1003'))

    def test_no_result_because_of_the_custom_filter(self):
        result = self.lookup('alice', 'default')

        assert_that(result['results'], empty())


class TestLDAPServiceIsDown(BaseDirdIntegrationTest):

    asset = 'ldap_service_down'

    def test_lookup(self):
        result = self.lookup('alice', 'default')

        assert_that(result['results'], empty())
