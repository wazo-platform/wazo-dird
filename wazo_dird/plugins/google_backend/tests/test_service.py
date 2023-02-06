# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
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
        formatted_contact = self.formatter.format(self.google_contact)
        assert_that(formatted_contact, has_entries(id='3ef7a14009000bb7'))

    def test_format_name(self):
        formatted_contact = self.formatter.format(self.google_contact)
        assert_that(formatted_contact, has_entries(name='Luigi Bros'))

    def test_format_first_name(self):
        formatted_contact = self.formatter.format(self.google_contact)
        assert_that(formatted_contact, has_entries(firstname='Luigi'))

    def test_format_last_name(self):
        formatted_contact = self.formatter.format(self.google_contact)
        assert_that(formatted_contact, has_entries(lastname='Bros'))

    def test_multiple_numbers(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                numbers_by_label=has_entries(
                    mobile='5555558888', home='5555554321', work='5555551234'
                ),
                numbers=contains_inanyorder('5555558888', '5555554321', '5555551234'),
                numbers_except_label=has_entries(
                    mobile=has_items('5555554321', '5555551234'),
                    home=has_items('5555558888', '5555551234'),
                ),
            ),
        )

    def test_multiple_emails(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                emails=contains(
                    has_entries(address='luigi_bros@caramail.com', label='Old'),
                    has_entries(address='luigi2@example.com', label='New'),
                ),
            ),
        )

    def test_organization(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                organizations=contains(
                    has_entries(name='Mushroom Kingdom', title='Plumber'),
                ),
            ),
        )

    def test_addresses(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                addresses=contains(
                    has_entries(
                        address='1600 Pennsylvania Avenue NW\\nWashington, DC 20500\\nUS',
                        label='work',
                    ),
                    has_entries(
                        address='24 Sussex Dr\\nOttawa, ON K1M 1M4\\nCA', label='home'
                    ),
                ),
            ),
        )

    def test_note(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(note='Notes user 02'),
        )
