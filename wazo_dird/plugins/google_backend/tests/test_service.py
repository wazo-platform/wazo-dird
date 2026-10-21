# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

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
    instance_of,
    raises,
    same_instance,
)

from .. import services
from ..exceptions import GoogleTokenRejectedException, GoogleUnavailableException


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


def _response(body, status_code=200, chunks=None):
    response = MagicMock(status_code=status_code)
    response.__enter__.return_value = response
    response.iter_content.return_value = chunks or [json.dumps(body).encode()]
    return response


def _google_error(reason):
    return {'error': {'code': 403, 'details': [{'reason': reason}]}}


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
        results = self._fetch_concurrently(get, 5, _response(self.contacts))

        assert_that(get.call_count, equal_to(1))
        assert_that(results, contains_exactly(*[has_length(2)] * 5))

    def test_concurrent_misses_share_a_failure(self, get):
        results = self._fetch_concurrently(
            get, 5, _response({}, 429), _response(self.contacts)
        )

        assert_that(get.call_count, equal_to(1))
        assert_that(
            results, contains_exactly(*[instance_of(GoogleUnavailableException)] * 5)
        )
        assert_that(len(self.service.get_all_contacts('token')), equal_to(2))

    def _fetch_concurrently(self, get, count, *responses):
        """Fetch from count threads; Google answers once the other threads
        all wait on the download"""
        release = threading.Event()
        waiting = threading.Semaphore(0)
        remaining = list(responses)

        def slow_get(*args, **kwargs):
            release.wait(5)
            return remaining.pop(0)

        class SignalingFuture(services.Future):
            def result(self, timeout=None):
                waiting.release()
                return super().result(timeout)

        results: list[object] = []

        def fetch():
            try:
                results.append(self.service.get_all_contacts('token'))
            except GoogleUnavailableException as e:
                results.append(e)

        get.side_effect = slow_get
        threads = [threading.Thread(target=fetch) for _ in range(count)]
        with patch.object(services, 'Future', SignalingFuture):
            for thread in threads:
                thread.start()
            for _ in range(count - 1):
                waiting.acquire(timeout=5)
            release.set()
            for thread in threads:
                thread.join(5)
        return results

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

    def test_google_failure_is_unavailable_without_google_details(self, get):
        get.return_value = _response({}, 500)

        with self.assertRaises(GoogleUnavailableException) as raised:
            self.service.get_all_contacts('token')

        assert_that(raised.exception.status_code, equal_to(503))
        assert_that(raised.exception.details, equal_to({}))

    def test_rejected_token_is_not_an_outage(self, get):
        responses = [
            _response({}, 401),
            _response(_google_error(services.TOKEN_SCOPE_REASON), 403),
        ]
        for response in responses:
            get.return_value = response

            with self.assertRaises(GoogleTokenRejectedException) as raised:
                self.service.get_all_contacts('token')

            assert_that(raised.exception.status_code, equal_to(403))
            assert_that(raised.exception.details, equal_to({}))

    def test_project_errors_are_an_outage(self, get):
        bodies: list[object] = [_google_error('SERVICE_DISABLED'), {}, None]
        for body in bodies:
            get.return_value = _response(body, 403)

            assert_that(
                calling(self.service.get_all_contacts).with_args('token'),
                raises(GoogleUnavailableException),
            )

    def test_invalid_body_raises_unavailable(self, get):
        bodies: list[object] = [
            None,
            [],
            'contacts',
            {'connections': None},
            {'connections': ['x']},
            {'connections': [{'names': 'x'}]},
            {'connections': [], 'nextPageToken': 1},
        ]
        for body in bodies:
            get.return_value = _response(body)

            assert_that(
                calling(self.service.get_all_contacts).with_args('token'),
                raises(GoogleUnavailableException),
            )

    def test_body_that_is_not_json_raises_unavailable(self, get):
        get.return_value = _response(None, chunks=[b'{"conn'])

        assert_that(
            calling(self.service.get_all_contacts).with_args('token'),
            raises(GoogleUnavailableException),
        )

    def test_slow_body_stops_at_the_deadline(self, get):
        clock = [0.0]

        def slow_chunks(*args, **kwargs):
            for _ in range(10):
                clock[0] += 9
                yield b' '

        response = _response({})
        response.iter_content.side_effect = slow_chunks
        get.return_value = response
        with patch.object(services, 'DOWNLOAD_TIMEOUT', 60), patch.object(
            services.time, 'monotonic', side_effect=lambda: clock[0]
        ):
            assert_that(
                calling(self.service.get_all_contacts).with_args('token'),
                raises(GoogleUnavailableException),
            )

        assert_that(clock[0], equal_to(63))

    def test_connection_error_raises_unavailable(self, get):
        get.side_effect = requests.ConnectionError()

        assert_that(
            calling(self.service.get_all_contacts).with_args('token'),
            raises(GoogleUnavailableException),
        )

    def test_download_stops_at_the_deadline(self, get):
        clock = [0.0]
        timeouts = []

        def slow_google(*args, **kwargs):
            timeouts.append(kwargs['timeout'])
            clock[0] += 27
            return _response({'connections': [], 'nextPageToken': 'next'})

        get.side_effect = slow_google
        with patch.object(services, 'DOWNLOAD_TIMEOUT', 60), patch.object(
            services.time, 'monotonic', side_effect=lambda: clock[0]
        ):
            assert_that(
                calling(self.service.get_all_contacts).with_args('token'),
                raises(GoogleUnavailableException),
            )

        # 60 seconds: three pages of 27 seconds, the third one given the 6
        # seconds left instead of the 10 of a request
        assert_that(timeouts, contains_exactly(10, 10, 6))

    def test_waiters_give_up_at_the_download_timeout(self, get):
        cache = services.ContactsCache(ttl=300)
        fetching = threading.Event()
        release = threading.Event()

        def slow_fetch():
            fetching.set()
            release.wait(5)
            return []

        fetcher = threading.Thread(target=cache.get_or_fetch, args=('a', slow_fetch))
        try:
            fetcher.start()
            fetching.wait(5)
            with patch.object(services, 'DOWNLOAD_TIMEOUT', 0.01):
                assert_that(
                    calling(cache.get_or_fetch).with_args('a', Mock()),
                    raises(GoogleUnavailableException),
                )
            assert_that(fetcher.is_alive(), equal_to(True))
        finally:
            release.set()
            fetcher.join(5)

    def test_requests_have_a_timeout(self, get):
        get.return_value = _response(self.contacts)

        self.service.get_all_contacts('token')

        assert_that(get.call_args.kwargs['timeout'], equal_to(services.REQUEST_TIMEOUT))

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


class TestSharedContactsCache(unittest.TestCase):
    def test_zero_disables_the_shared_cache(self):
        config = {'google_backend': {'contacts_cache_ttl': 0}}

        assert_that(services.shared_contacts_cache(config), equal_to(None))

    def test_sources_and_view_share_one_cache(self):
        self.addCleanup(setattr, services, '_shared_cache', None)
        config = {'google_backend': {'contacts_cache_ttl': 120}}

        assert_that(
            services.shared_contacts_cache(config),
            same_instance(services.shared_contacts_cache(dict(config))),
        )


class TestContactsCache(unittest.TestCase):
    def test_expired_entries_are_dropped_on_write(self):
        cache = services.ContactsCache(ttl=300)

        with patch.object(services.time, 'monotonic', return_value=1000):
            cache.get_or_fetch('a', Mock(return_value=[]))
        with patch.object(services.time, 'monotonic', return_value=1300):
            cache.get_or_fetch('b', Mock(return_value=[]))

        assert_that(cache._entries, has_length(1))

    def test_oldest_entry_is_evicted_when_full(self):
        cache = services.ContactsCache(ttl=300)
        cache.MAX_CONTACTS = 2

        for token in ('a', 'b', 'c'):
            cache.get_or_fetch(token, Mock(return_value=[{'id': token}]))

        fetch = Mock(return_value=[])
        cache.get_or_fetch('b', fetch)
        cache.get_or_fetch('c', fetch)
        fetch.assert_not_called()
        cache.get_or_fetch('a', fetch)
        fetch.assert_called_once_with()

    def test_entries_are_evicted_until_the_contacts_fit(self):
        cache = services.ContactsCache(ttl=300)
        cache.MAX_CONTACTS = 3

        for token in ('a', 'b', 'c'):
            cache.get_or_fetch(token, Mock(return_value=[{'id': token}]))
        cache.get_or_fetch('d', Mock(return_value=[{'id': 'd1'}, {'id': 'd2'}]))

        assert_that(
            list(cache._entries), contains_exactly(cache._key('c'), cache._key('d'))
        )
        assert_that(cache._contact_count, equal_to(3))

    def test_contacts_above_the_limit_are_not_cached(self):
        cache = services.ContactsCache(ttl=300)
        cache.MAX_CONTACTS = 2
        cache.get_or_fetch('a', Mock(return_value=[{'id': 'a'}]))

        contacts = [{'id': 'b1'}, {'id': 'b2'}, {'id': 'b3'}]
        fetch = Mock(return_value=contacts)
        assert_that(cache.get_or_fetch('b', fetch), equal_to(contacts))
        assert_that(cache.get_or_fetch('b', fetch), equal_to(contacts))

        assert_that(fetch.call_count, equal_to(2))
        assert_that(list(cache._entries), contains_exactly(cache._key('a')))
        assert_that(cache._contact_count, equal_to(1))

    def test_interrupted_fetch_does_not_block_later_fetches(self):
        cache = services.ContactsCache(ttl=300)

        assert_that(
            calling(cache.get_or_fetch).with_args(
                'a', Mock(side_effect=KeyboardInterrupt)
            ),
            raises(KeyboardInterrupt),
        )

        fetch = Mock(return_value=[{'id': 'a'}])
        assert_that(cache.get_or_fetch('a', fetch), contains_exactly({'id': 'a'}))
        fetch.assert_called_once_with()
