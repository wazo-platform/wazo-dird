# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_items,
)

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
                emails=contains_exactly(
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
                organizations=contains_exactly(
                    has_entries(name='Mushroom Kingdom', title='Plumber'),
                ),
            ),
        )

    def test_addresses(self):
        formatted_contact = self.formatter.format(self.google_contact)

        assert_that(
            formatted_contact,
            has_entries(
                addresses=contains_exactly(
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


def _person(id_, name):
    return {
        'names': [{'displayName': name, 'metadata': {'source': {'id': id_}}}],
    }


def _response(body, status_code=200):
    return Mock(status_code=status_code, json=Mock(return_value=body), text='')


@patch('wazo_dird.plugins.google_backend.services.requests.get')
class TestGoogleServiceCache(unittest.TestCase):
    contacts = {'connections': [_person('1', 'Mario'), _person('2', 'Luigi')]}

    def setUp(self):
        services._contacts_cache.clear()
        services._search_warmups.clear()
        self.service = services.GoogleService(contacts_cache_ttl=300)

    def tearDown(self):
        services._contacts_cache.clear()
        services._search_warmups.clear()

    def test_contacts_are_fetched_once_per_token(self, get):
        get.return_value = _response(self.contacts)

        first = self.service.get_all_contacts('token')
        second = services.GoogleService(300).get_all_contacts('token')

        assert_that(get.call_count, equal_to(1))
        assert_that(second, equal_to(first))
        assert_that(first, contains_exactly(has_entries(id='1'), has_entries(id='2')))

    def test_tokens_do_not_share_contacts(self, get):
        get.return_value = _response(self.contacts)

        self.service.get_all_contacts('token-a')
        self.service.get_all_contacts('token-b')

        assert_that(get.call_count, equal_to(2))

    def test_expired_contacts_are_fetched_again(self, get):
        get.return_value = _response(self.contacts)

        with patch.object(services.time, 'monotonic', return_value=1000):
            self.service.get_all_contacts('token')
        with patch.object(services.time, 'monotonic', return_value=1300):
            self.service.get_all_contacts('token')

        assert_that(get.call_count, equal_to(2))

    def test_zero_ttl_disables_the_cache(self, get):
        get.return_value = _response(self.contacts)
        service = services.GoogleService(contacts_cache_ttl=0)

        service.get_all_contacts('token')
        service.get_all_contacts('token')

        assert_that(get.call_count, equal_to(2))

    def test_failed_fetch_is_not_cached(self, get):
        get.side_effect = [_response({}, 429), _response(self.contacts)]

        assert_that(self.service.get_all_contacts('token'), equal_to([]))
        assert_that(len(self.service.get_all_contacts('token')), equal_to(2))

    def test_callers_cannot_alter_the_cached_list(self, get):
        get.return_value = _response(self.contacts)

        self.service.get_all_contacts('token').clear()

        assert_that(len(self.service.get_all_contacts('token')), equal_to(2))

    def test_all_pages_are_fetched(self, get):
        get.side_effect = [
            _response(
                {'connections': [_person('1', 'Mario')], 'nextPageToken': 'next'}
            ),
            _response({'connections': [_person('2', 'Luigi')]}),
        ]

        contacts = self.service.get_all_contacts('token')

        assert_that(
            contacts, contains_exactly(has_entries(id='1'), has_entries(id='2'))
        )
        assert_that(
            get.call_args_list[1].kwargs['params'], has_entries(pageToken='next')
        )

    def test_search_warms_up_once_per_token(self, get):
        get.return_value = _response({'results': [{'person': _person('1', 'Mario')}]})

        self.service.get_contacts('token', search='mar')
        self.service.get_contacts('token', search='mari')

        queries = [call.kwargs['params'].get('query') for call in get.call_args_list]
        assert_that(queries, contains_exactly(None, 'mar', 'mari'))


class TestTokenCache(unittest.TestCase):
    def test_oldest_entry_is_evicted_when_full(self):
        cache = services._TokenCache()
        cache.MAX_ENTRIES = 2

        cache.set('a', 'A', 300)
        cache.set('b', 'B', 300)
        cache.set('c', 'C', 300)

        assert_that(cache.get('a'), equal_to(None))
        assert_that(cache.get('b'), equal_to('B'))
        assert_that(cache.get('c'), equal_to('C'))
