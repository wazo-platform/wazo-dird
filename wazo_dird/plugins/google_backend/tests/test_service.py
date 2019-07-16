# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    has_entries,
)

from ..import services


class TestGoogleContactFormatter(unittest.TestCase):

    def setUp(self):
        self.formatter = services.ContactFormatter()

    def test_format_id(self):
        google_contact = {
            'id': {
                '$t': 'http://www.google.com/m8/feeds/contacts/me%40example.com/base/72b6b4840bf772e6',
            },
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(
            id='72b6b4840bf772e6',
        ))

    def test_format_name(self):
        google_contact = {
            'title': {
                '$t': 'Joe Blow',
                'type': 'text',
            }
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(
            name='Joe Blow',
        ))

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
            ],
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(
            numbers_by_label=has_entries(
                mobile='+15551234567',
                home='+15551239876',
                custom='5551231111',
            ),
            numbers=contains_inanyorder(
                '+15551239876',
                '5551231111',
                '+15551234567',
            ),
        ))

    def test_multiple_emails(self):
        google_contact = {
            'gd$email': [
                {
                    'address': 'home@example.com',
                    'rel': 'http://schemas.google.com/g/2005#home',
                },
                {
                    'address': 'other@example.com',
                    'label': 'custom',
                },
            ],
        }

        formatted_contact = self.formatter.format(google_contact)

        assert_that(formatted_contact, has_entries(
            emails=contains(
                'home@example.com',
                'other@example.com',
            ),
        ))
