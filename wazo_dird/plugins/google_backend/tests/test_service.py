# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, contains, contains_inanyorder, has_entries

from .. import services


class TestGoogleContactFormatter(unittest.TestCase):
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
            formatted_contact, has_entries(note='Notey'),
        )
