# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import unittest
from unittest.mock import Mock, patch

import requests
from hamcrest import (
    assert_that,
    calling,
    contains_exactly,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_items,
    has_length,
    raises,
    same_instance,
)

from .. import services
from ..exceptions import GoogleUnavailableException


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
        self.cache = services.ContactsCache(ttl=300)
        self.service = services.GoogleService(self.cache)

    def test_contacts_are_fetched_once_per_token(self, get):
        get.return_value = _response(self.contacts)

        first = self.service.get_all_contacts('token')
        second = services.GoogleService(self.cache).get_all_contacts('token')

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

    def test_no_cache_fetches_every_time(self, get):
        get.return_value = _response(self.contacts)
        service = services.GoogleService()

        service.get_all_contacts('token')
        service.get_all_contacts('token')

        assert_that(get.call_count, equal_to(2))

    def test_concurrent_misses_fetch_once(self, get):
        fetching = threading.Event()
        release = threading.Event()

        def slow_get(*args, **kwargs):
            fetching.set()
            release.wait(5)
            return _response(self.contacts)

        get.side_effect = slow_get
        results = []

        def fetch():
            results.append(self.service.get_all_contacts('token'))

        threads = [threading.Thread(target=fetch) for _ in range(5)]
        threads[0].start()
        fetching.wait(5)
        for thread in threads[1:]:
            thread.start()
        release.set()
        for thread in threads:
            thread.join(5)

        assert_that(get.call_count, equal_to(1))
        assert_that(results, contains_exactly(*[has_length(2)] * 5))

    def test_failed_fetch_raises_and_is_not_cached(self, get):
        get.side_effect = [_response({}, 429), _response(self.contacts)]

        assert_that(
            calling(self.service.get_all_contacts).with_args('token'),
            raises(GoogleUnavailableException),
        )
        assert_that(len(self.service.get_all_contacts('token')), equal_to(2))

    def test_failed_page_raises_and_is_not_cached(self, get):
        first_page = _response(
            {'connections': [_person('1', 'Mario')], 'nextPageToken': 'next'}
        )
        second_page = _response({'connections': [_person('2', 'Luigi')]})
        get.side_effect = [first_page, _response({}, 500), first_page, second_page]

        assert_that(
            calling(self.service.get_all_contacts).with_args('token'),
            raises(GoogleUnavailableException),
        )
        assert_that(
            self.service.get_all_contacts('token'),
            contains_exactly(has_entries(id='1'), has_entries(id='2')),
        )

    def test_google_status_is_in_the_error_details(self, get):
        get.return_value = _response({}, 403)

        try:
            self.service.get_all_contacts('token')
        except GoogleUnavailableException as e:
            assert_that(e.status_code, equal_to(503))
            assert_that(e.details, has_entries(google_status_code=403))
        else:
            self.fail('GoogleUnavailableException not raised')

    def test_connection_error_raises_unavailable(self, get):
        get.side_effect = requests.ConnectionError()

        assert_that(
            calling(self.service.get_all_contacts).with_args('token'),
            raises(GoogleUnavailableException),
        )

    def test_requests_have_a_timeout(self, get):
        get.return_value = _response(self.contacts)

        self.service.get_all_contacts('token')

        assert_that(get.call_args.kwargs['timeout'], equal_to(services.REQUEST_TIMEOUT))

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

    def test_searches_filter_the_cached_contacts(self, get):
        get.return_value = _response(self.contacts)

        mario, mario_total = self.service.get_contacts('token', ['name'], search='MAR')
        luigi, luigi_total = self.service.get_contacts('token', ['name'], search='uig')

        assert_that(get.call_count, equal_to(1))
        assert_that(get.call_args.args[0], equal_to(services.GoogleService.people_url))
        assert_that(mario, contains_exactly(has_entries(id='1')))
        assert_that(luigi, contains_exactly(has_entries(id='2')))
        assert_that((mario_total, luigi_total), equal_to((1, 1)))

    def test_search_matches_the_searched_columns(self, get):
        luigi = TestGoogleContactFormatter.google_contact
        get.return_value = _response({'connections': [_person('1', 'Mario'), luigi]})

        def search(term, columns):
            contacts, _ = self.service.get_contacts('token', columns, search=term)
            return [contact['name'] for contact in contacts]

        assert_that(search('caramail', ['name']), equal_to([]))
        assert_that(search('caramail', ['emails']), contains_exactly('Luigi Bros'))
        assert_that(
            search('plumber', ['organizations']), contains_exactly('Luigi Bros')
        )
        assert_that(search('5555558888', ['numbers']), contains_exactly('Luigi Bros'))
        assert_that(
            search('bros', ['firstname', 'lastname']), contains_exactly('Luigi Bros')
        )
        assert_that(search('bros', []), equal_to([]))


class TestMatchesSearch(unittest.TestCase):
    def test_non_string_values_are_ignored(self):
        contact = {
            'name': None,
            'note': 42,
            'emails': [{'address': 'mario@example.com', 'label': None}],
        }

        assert_that(
            services.matches_search(contact, 'mario', ['name', 'note', 'emails']),
            equal_to(True),
        )
        assert_that(
            services.matches_search(contact, '42', ['name', 'note', 'emails']),
            equal_to(False),
        )

    def test_dict_columns_match_their_values(self):
        contact = {'numbers_by_label': {'mobile': '5555551234'}}

        assert_that(
            services.matches_search(contact, '555', ['numbers_by_label']),
            equal_to(True),
        )
        assert_that(
            services.matches_search(contact, 'mobile', ['numbers_by_label']),
            equal_to(False),
        )


class TestContactsCacheTTL(unittest.TestCase):
    def test_default(self):
        assert_that(
            services.contacts_cache_ttl({}),
            equal_to(services.DEFAULT_CONTACTS_CACHE_TTL),
        )

    def test_configured(self):
        config = {'google_backend': {'contacts_cache_ttl': 60}}

        assert_that(services.contacts_cache_ttl(config), equal_to(60))

    def test_invalid_values_use_the_default(self):
        for ttl in ('300', None, -1, True, 1.5):
            config = {'google_backend': {'contacts_cache_ttl': ttl}}

            assert_that(
                services.contacts_cache_ttl(config),
                equal_to(services.DEFAULT_CONTACTS_CACHE_TTL),
            )

    def test_zero_disables_the_shared_cache(self):
        config = {'google_backend': {'contacts_cache_ttl': 0}}

        assert_that(services.shared_contacts_cache(config), equal_to(None))

    def test_sources_and_view_share_one_cache(self):
        config = {'google_backend': {'contacts_cache_ttl': 120}}

        assert_that(
            services.shared_contacts_cache(config),
            same_instance(services.shared_contacts_cache(dict(config))),
        )


class TestContactsCache(unittest.TestCase):
    def test_oldest_entry_is_evicted_when_full(self):
        cache = services.ContactsCache(ttl=300)
        cache.MAX_ENTRIES = 2

        for token in ('a', 'b', 'c'):
            cache.get_or_fetch(token, Mock(return_value=[{'id': token}]))

        fetch = Mock(return_value=[])
        cache.get_or_fetch('b', fetch)
        cache.get_or_fetch('c', fetch)
        fetch.assert_not_called()
        cache.get_or_fetch('a', fetch)
        fetch.assert_called_once_with()
