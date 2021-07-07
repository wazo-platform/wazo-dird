# Copyright 2019-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, contains, contains_inanyorder, has_entries, has_items

from .. import services


class TestGoogleContactFormatter(unittest.TestCase):

    google_contact = {
        "resourceName": "people/c4537272446000040887",
        "etag": "%EgwQQDcJPgECPQwLPy4aBAIBBwUiDDBMeWYxSWljM2pnPQ==",
        "names": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
                },
                "displayName": "Luigi Bros",
                "familyName": "Bros",
                "givenName": "Luigi",
                "displayNameLastFirst": "Bros, Luigi",
                "unstructuredName": "Luigi Bros",
            }
        ],
        "addresses": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
                },
                "formattedValue": "1600 Pennsylvania Avenue NW\\nWashington, DC 20500\\nUS",
                "type": "work",
                "formattedType": "Work",
                "streetAddress": "1600 Pennsylvania Avenue NW",
                "city": "Washington",
                "region": "DC",
                "postalCode": "20500",
                "country": "US",
                "countryCode": "US",
            },
            {
                "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
                "formattedValue": "24 Sussex Dr\\nOttawa, ON K1M 1M4\\nCA",
                "type": "home",
                "formattedType": "Home",
                "streetAddress": "24 Sussex Dr",
                "city": "Ottawa",
                "region": "ON",
                "postalCode": "K1M 1M4",
                "country": "CA",
                "countryCode": "CA",
            },
        ],
        "emailAddresses": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
                },
                "value": "luigi_bros@caramail.com",
                "type": "Old",
                "formattedType": "Old",
            },
            {
                "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
                "value": "luigi2@example.com",
                "type": "New",
                "formattedType": "New",
            },
        ],
        "phoneNumbers": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
                },
                "value": "555-555-1234",
                "type": "work",
                "formattedType": "Work",
            },
            {
                "metadata": {"source": {"type": "CONTACT", "id": "38ad74eb0f67d221"}},
                "value": "555-555-4321",
                "type": "home",
                "formattedType": "Home",
            },
            {
                "metadata": {"source": {"type": "CONTACT", "id": "38ad74eb0f67d221"}},
                "value": "(555) 555-8888",
                "type": "mobile",
                "formattedType": "Mobile",
            },
        ],
        "biographies": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
                },
                "value": "Notes user 02",
                "contentType": "TEXT_PLAIN",
            }
        ],
        "organizations": [
            {
                "metadata": {
                    "primary": True,
                    "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
                },
                "name": "Mushroom Kingdom",
                "title": "Plumber",
            }
        ],
    }

    def setUp(self):
        self.formatter = services.ContactFormatter()

    def test_format_id(self):
        google_contact = {
            'id': {
                '$t': 'http://www.google.com/m8/feeds/contacts/me%40example.com/base/72b6b4840bf772e6'
            }
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(id='72b6b4840bf772e6'))

    def test_format_name(self):
        google_contact = {'title': {'$t': 'Joe Blow', 'type': 'text'}}

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(name='Joe Blow'))

    def test_format_name_when_fullname(self):
        google_contact = {
            'title': {'$t': 'Test User1', 'type': 'text'},
            'gd$name': {'gd$fullName': {'$t': 'Test FullName'}},
        }

        formatted_contact = self.formatter.format(google_contact)
        assert_that(formatted_contact, has_entries(name='Test FullName'))

    def test_format_first_name(self):
        google_contact = {'gd$name': {'gd$givenName': {'$t': 'Test'}}}

        formatted_contact = self.formatter.format(google_contact)
        assert_that(formatted_contact, has_entries(firstname='Test'))

    def test_format_last_name(self):
        google_contact = {'gd$name': {'gd$familyName': {'$t': 'Family'}}}

        formatted_contact = self.formatter.format(google_contact)
        assert_that(formatted_contact, has_entries(lastname='Family'))

    def test_multiple_numbers(self):
        google_contact = {
            'gd$phoneNumber': [
                {
                    'rel': 'http://schemas.google.com/g/2005#mobile',
                    'uri': 'tel:+1-555-123-4567',
                    '$t': '+1 555-123-4567',
                },
                {
                    'rel': 'http://schemas.google.com/g/2005#home',
                    'uri': 'tel:+1-555-123-9876',
                    '$t': '+1 5551239876',
                },
                {
                    'label': 'custom',
                    '$t': '(555) 123-1111',
                    'uri': 'tel:+1-555-123-1111',
                },
            ]
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                numbers_by_label=has_entries(
                    mobile='+15551234567', home='+15551239876', custom='5551231111'
                ),
                numbers=contains_inanyorder(
                    '+15551239876', '5551231111', '+15551234567'
                ),
                numbers_except_label=has_entries(
                    mobile=has_items('+15551239876', '5551231111'),
                    home=has_items('+15551234567', '5551231111'),
                ),
            ),
        )

    def test_multiple_emails(self):
        google_contact = {
            'gd$email': [
                {
                    'address': 'home@example.com',
                    'rel': 'http://schemas.google.com/g/2005#home',
                },
                {'address': 'other@example.com', 'label': 'custom'},
                {'address': 'other2@example.com'},
            ]
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                emails=contains(
                    has_entries(address='home@example.com', label='home'),
                    has_entries(address='other@example.com', label='custom'),
                    has_entries(address='other2@example.com', label=''),
                ),
            ),
        )

    def test_organization(self):
        google_contact = {
            'gd$organization': [
                {
                    'gd$orgTitle': {'$t': 'Tester'},
                    'gd$orgName': {'$t': 'Test Company'},
                },
                {'gd$orgTitle': {'$t': 'President'}, 'gd$orgName': {'$t': 'Acme'}},
            ],
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                organizations=contains(
                    has_entries(name='Test Company', title='Tester'),
                    has_entries(name='Acme', title='President'),
                ),
            ),
        )

    def test_addresses(self):
        google_contact = {
            'gd$structuredPostalAddress': [
                {
                    'rel': 'http://schemas.google.com/g/2005#home',
                    'gd$formattedAddress': {'$t': 'First address'},
                },
                {
                    'label': 'Test address',
                    'gd$formattedAddress': {'$t': 'Second address'},
                },
            ],
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                addresses=contains(
                    has_entries(address='First address', label='home'),
                    has_entries(address='Second address', label='Test address'),
                ),
            ),
        )

    def test_note(self):
        google_contact = {'content': {'$t': 'Notey'}}

        formatted_contact = self.formatter.format(google_contact)

        assert_that(
            formatted_contact,
            has_entries(note='Notey'),
        )
