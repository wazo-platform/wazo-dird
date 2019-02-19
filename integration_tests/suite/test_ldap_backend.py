# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import ldap
import time

from collections import namedtuple
from ldap.modlist import addModlist
from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_entry,
)

from .base_dird_integration_test import (
    BaseDirdIntegrationTest,
    VALID_UUID,
)
from .helpers.fixtures import http as fixtures


Contact = namedtuple('Contact', ['firstname', 'lastname', 'number', 'city'])


class LDAPHelper:

    BASE_DN = 'dc=wazo-dird,dc=wazo,dc=community'
    ADMIN_DN = 'cn=admin,{}'.format(BASE_DN)
    ADMIN_PASSWORD = 'wazopassword'
    QUEBEC_DN = 'ou=québec,{}'.format(BASE_DN)

    def __init__(self, ldap_uri):
        self._ldap_obj = ldap.initialize(ldap_uri)
        self._ldap_obj.simple_bind_s(self.ADMIN_DN, self.ADMIN_PASSWORD)

    def add_ou_quebec(self):
        modlist = addModlist({
            'objectClass': [b'organizationalUnit'],
            'ou': [b'quebec'],
        })

        self._ldap_obj.add_s(self.QUEBEC_DN, modlist)

    def add_contact(self, contact):
        cn = '{} {}'.format(contact.firstname, contact.lastname)
        dn = 'cn={},{}'.format(cn, self.QUEBEC_DN)
        modlist = addModlist({
            'objectClass': [b'inetOrgPerson'],
            'cn': [cn.encode('utf-8')],
            'givenName': [contact.firstname.encode('utf-8')],
            'sn': [contact.lastname.encode('utf-8')],
            'telephoneNumber': [contact.number.encode('utf-8')],
            'l': [contact.city.encode('utf-8')],
        })

        self._ldap_obj.add_s(dn, modlist)
        search_dn, result = self._ldap_obj.search_s(dn, ldap.SCOPE_BASE, attrlist=['entryUUID'])[0]
        return result['entryUUID'][0].decode('utf-8')


def add_contacts(contacts, ldap_uri):
    for _ in range(10):
        try:
            helper = LDAPHelper(ldap_uri)
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
        super().setUpClass()
        ldap_uri = 'ldap://localhost:{port}'.format(port=cls.service_port(389, 'slapd'))

        try:
            cls.entry_uuids = add_contacts(cls.CONTACTS, ldap_uri)
        except Exception:
            super().tearDownClass()
            raise

    def setUp(self):
        super().setUp()
        body = {
            'name': 'test_ldap',
            'ldap_uri': 'ldap://slapd',
            'ldap_base_dn': 'ou=québec,dc=wazo-dird,dc=wazo,dc=community',
            'ldap_username': 'cn=admin,dc=wazo-dird,dc=wazo,dc=community',
            'ldap_password': 'wazopassword',
            'unique_column': 'entryUUID',
            'searched_columns': ['cn', 'telephoneNumber'],
            'first_matched_columns': ['telephoneNumber'],
            'format_columns':  {
                'firstname': "{givenName}",
                'lastname': "{sn}",
                'number': "{telephoneNumber}",
                'reverse': "{cn}",
            }
        }
        source = self.client.ldap_source.create(body)
        self.source_uuid = source['uuid']

    def tearDown(self):
        self.client.ldap_source.delete(self.source_uuid)
        super().tearDown()

    def test_lookup_on_cn(self):
        result = self.lookup('Ali', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'Wonderland', '1001'))

    def test_lookup_on_telephone_number(self):
        result = self.lookup('1001', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Alice', 'Wonderland', '1001'))

    def test_lookup_with_non_ascii_characters(self):
        result = self.lookup('ç', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('François', 'Hollande', '1004'))

    def test_reverse_lookup(self):
        result = self.reverse('1001', 'default', VALID_UUID)

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

    def setUp(self):
        body = {
            'name': 'test_ldap',
            'ldap_uri': 'ldap://slapd',
            'ldap_base_dn': 'ou=québec,dc=wazo-dird,dc=wazo,dc=community',
            'ldap_username': 'cn=admin,dc=wazo-dird,dc=wazo,dc=community',
            'ldap_password': 'wazopassword',
            'ldap_custom_filter': '(l=Québec)',
            'unique_column': 'entryUUID',
            'searched_columns': ['cn', 'telephoneNumber'],
            'first_matched_columns': ['telephoneNumber'],
            'format_columns':  {
                'firstname': "{givenName}",
                'lastname': "{sn}",
                'number': "{telephoneNumber}",
                'reverse': "{cn}",
            }
        }
        super().setUp()
        source = self.client.ldap_source.create(body)
        self.source_uuid = source['uuid']

    def tearDown(self):
        self.client.ldap_source.delete(self.source_uuid)
        super().tearDown()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ldap_uri = 'ldap://localhost:{port}'.format(port=cls.service_port(389, 'slapd'))

        try:
            cls.entry_uuids = add_contacts(cls.CONTACTS, ldap_uri)
        except Exception:
            super().tearDownClass()
            raise

    def test_lookup_on_cn(self):
        result = self.lookup('charlé', 'default')

        assert_that(result['results'][0]['column_values'],
                    contains('Charlé', 'Doe', '1003'))

    def test_no_result_because_of_the_custom_filter(self):
        result = self.lookup('alice', 'default')

        assert_that(result['results'], empty())


class TestLDAPServiceIsInnactive(BaseDirdIntegrationTest):

    asset = 'ldap_service_innactive'

    @fixtures.ldap_source(
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        }
    )
    def test_lookup(self, _):
        result = self.lookup('alice', 'default')

        start = time.time()
        assert_that(result['results'], empty())
        assert_that(time.time() - start < 3, 'dird should block on the ldap')


class TestLDAPServiceIsDown(BaseDirdIntegrationTest):

    asset = 'ldap_service_down'

    @fixtures.ldap_source(
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        }
    )
    def test_lookup(self, _):
        result = self.lookup('alice', 'default')

        assert_that(result['results'], empty())
