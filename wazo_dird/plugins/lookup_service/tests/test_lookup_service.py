# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import time
import unittest
from unittest.mock import Mock, patch

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    less_than,
)

from wazo_dird import contacts_cache
from wazo_dird.exception import SourceListError

from ..plugin import _LookupService
from .fakes import FakeSource, FakeSourceManager, config, contacts, profile

TENANT = 'tenant-uuid'


def _service(sources, **conf):
    manager = FakeSourceManager(sources)
    service = _LookupService(config(**conf), manager, Mock())
    return service, manager


def _names(items):
    return [item.fields['name'] for item in items]


def _page(service, profiles, limit=1000, offset=0, user_uuid=None, token='token'):
    return service.list_page(profiles, TENANT, user_uuid, token, limit, offset)


class TestListAllFanOut(unittest.TestCase):
    def test_a_source_shared_by_two_profiles_is_listed_once(self):
        shared = FakeSource('shared', contacts('s', 3))
        service, _ = _service({'u-shared': shared})
        profiles = [
            profile('p1', lookup=['u-shared']),
            profile('p2', lookup=['u-shared'], favorites=['u-shared']),
        ]

        items, total, missing = _page(service, profiles)

        assert_that(len(shared.list_calls), equal_to(1))
        assert_that(total, equal_to(3))
        assert_that(missing, empty())

    def test_reverse_only_and_favorites_only_sources_are_listed(self):
        sources = {
            'u-a': FakeSource('a', [{'id': '1', 'name': 'from lookup'}]),
            'u-b': FakeSource('b', [{'id': '1', 'name': 'from reverse'}]),
            'u-c': FakeSource('c', [{'id': '1', 'name': 'from favorites'}]),
        }
        service, _ = _service(sources)
        profiles = [
            profile('p1', lookup=['u-a']),
            profile('p2', reverse=['u-b'], favorites=['u-c']),
        ]

        items, total, _ = _page(service, profiles)

        assert_that(
            _names(items),
            contains_exactly('from lookup', 'from reverse', 'from favorites'),
        )
        assert_that(total, equal_to(3))

    def test_other_services_and_unknown_sources_are_not_listed(self):
        unrelated = FakeSource('unrelated', contacts('u', 1))
        service, _ = _service({'u-unrelated': unrelated})
        profiles = [profile('p1', personal=['u-unrelated'], lookup=['u-gone'])]

        items, total, missing = _page(service, profiles)

        assert_that(unrelated.list_calls, empty())
        assert_that((items, total, missing), equal_to(([], 0, [])))

    def test_the_fan_out_never_searches(self):
        # FakeSource.search raises: a listing that searched would miss it
        source = FakeSource('a', contacts('a', 2))
        service, _ = _service({'u-a': source})

        _, total, missing = _page(service, [profile('p', lookup=['u-a'])])

        assert_that((total, missing), equal_to((2, [])))

    def test_the_user_and_token_reach_the_sources(self):
        source = FakeSource('personal', [], cacheable=False)
        service, _ = _service({'u-p': source})

        _page(service, [profile('p', lookup=['u-p'])], user_uuid='user', token='tok')

        assert_that(
            source.list_calls,
            contains_exactly(has_entries(token='tok', user_uuid='user')),
        )

    def test_a_raising_and_a_timed_out_source_are_missing(self):
        gate = threading.Event()
        self.addCleanup(gate.set)
        ok = FakeSource('ok', contacts('o', 2))
        broken = FakeSource('broken', contacts('b', 2))
        broken.error = SourceListError('broken')
        slow = FakeSource('slow', contacts('l', 2))
        slow.gate = gate
        service, _ = _service(
            {'u-ok': ok, 'u-broken': broken, 'u-slow': slow}, timeout=0.2
        )
        profiles = [profile('p', lookup=['u-ok', 'u-broken', 'u-slow'])]

        started = time.monotonic()
        items, total, missing = _page(service, profiles)

        assert_that(time.monotonic() - started, less_than(2))
        assert_that(_names(items), contains_exactly('o 0', 'o 1'))
        assert_that(total, equal_to(2))
        assert_that(missing, contains_inanyorder('broken', 'slow'))

    def test_any_exception_of_a_source_makes_it_missing(self):
        broken = FakeSource('broken', [])
        broken.error = RuntimeError('a bug in a third-party backend')
        service, _ = _service({'u-b': broken})

        _, _, missing = _page(service, [profile('p', lookup=['u-b'])])

        assert_that(missing, contains_exactly('broken'))

    def test_the_profiles_timeouts_do_not_cut_the_listing(self):
        slow = FakeSource('slow', contacts('s', 1))
        slow.on_list = lambda: time.sleep(0.3)
        service, _ = _service({'u-s': slow}, timeout=5)
        p = profile('p', reverse=['u-s'])
        p['services']['reverse']['options'] = {'timeout': 0.05}

        items, _, missing = _page(service, [p])

        assert_that((_names(items), missing), equal_to((['s 0'], [])))


class TestListAllCache(unittest.TestCase):
    def setUp(self):
        self.shared = FakeSource('shared', contacts('s', 2))
        self.profiles = [profile('p', lookup=['u-s'])]

    def test_two_listings_within_the_delay_list_a_shared_source_once(self):
        service, _ = _service({'u-s': self.shared})

        with patch.object(contacts_cache.time, 'monotonic', return_value=1000):
            _page(service, self.profiles)
        with patch.object(contacts_cache.time, 'monotonic', return_value=1029):
            _page(service, self.profiles)
        assert_that(len(self.shared.list_calls), equal_to(1))
        with patch.object(contacts_cache.time, 'monotonic', return_value=1030):
            _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))

    def test_a_zero_ttl_lists_every_time(self):
        service, _ = _service({'u-s': self.shared}, cache_ttl=0)

        _page(service, self.profiles)
        _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))

    def test_a_source_above_the_bound_is_listed_every_time(self):
        service, _ = _service({'u-s': self.shared}, max_contacts=1)

        _page(service, self.profiles)
        items, total, _ = _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))
        assert_that((_names(items), total), equal_to((['s 0', 's 1'], 2)))

    def test_a_failure_is_not_cached(self):
        service, _ = _service({'u-s': self.shared})
        self.shared.error = SourceListError('shared')

        _, _, missing = _page(service, self.profiles)
        assert_that(missing, contains_exactly('shared'))
        self.shared.error = None
        _, total, missing = _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))
        assert_that((total, missing), equal_to((2, [])))

    def test_an_edit_forgets_the_cached_list(self):
        service, manager = _service({'u-s': self.shared})

        _page(service, self.profiles)
        manager.invalidate('u-s')
        _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))

    def test_an_edit_during_a_listing_keeps_that_list_out_of_the_cache(self):
        service, manager = _service({'u-s': self.shared})
        self.shared.on_list = lambda: manager.invalidate('u-s')

        _page(service, self.profiles)
        self.shared.on_list = None
        _page(service, self.profiles)

        assert_that(len(self.shared.list_calls), equal_to(2))

    def test_an_edit_of_a_source_never_listed_does_nothing(self):
        service, manager = _service({'u-s': self.shared})

        manager.invalidate('never-listed')

        _page(service, self.profiles)
        assert_that(len(self.shared.list_calls), equal_to(1))

    def test_user_scoped_and_written_sources_are_never_cached(self):
        sources = {
            f'u-{backend}': FakeSource(
                backend, contacts(backend, 1), cacheable=False, backend=backend
            )
            for backend in ('personal', 'phonebook', 'google', 'office365')
        }
        service, _ = _service(sources)
        profiles = [profile('p', lookup=list(sources))]

        _page(service, profiles)
        _page(service, profiles)

        for source in sources.values():
            assert_that(len(source.list_calls), equal_to(2), source.name)


class TestListCacheableBackends(unittest.TestCase):
    def test_only_tenant_wide_backends_are_cacheable(self):
        from wazo_dird.plugins.conference_backend.plugin import ConferencePlugin
        from wazo_dird.plugins.csv_backend.plugin import CSVPlugin
        from wazo_dird.plugins.csv_ws_backend.plugin import CSVWSPlugin
        from wazo_dird.plugins.google_backend.plugin import GooglePlugin
        from wazo_dird.plugins.ldap_backend.plugin import LDAPPlugin
        from wazo_dird.plugins.office365_backend.plugin import Office365Plugin
        from wazo_dird.plugins.personal_backend.plugin import PersonalBackend
        from wazo_dird.plugins.phonebook_backend.plugin import PhonebookPlugin
        from wazo_dird.plugins.wazo_user_backend.plugin import WazoUserPlugin

        cacheable = {
            plugin.__name__: plugin.list_cacheable
            for plugin in (
                ConferencePlugin,
                CSVPlugin,
                CSVWSPlugin,
                GooglePlugin,
                LDAPPlugin,
                Office365Plugin,
                PersonalBackend,
                PhonebookPlugin,
                WazoUserPlugin,
            )
        }

        assert_that(
            cacheable,
            equal_to(
                {
                    'ConferencePlugin': True,
                    'CSVPlugin': True,
                    'CSVWSPlugin': True,
                    'GooglePlugin': False,
                    'LDAPPlugin': True,
                    'Office365Plugin': False,
                    'PersonalBackend': False,
                    'PhonebookPlugin': False,
                    'WazoUserPlugin': True,
                }
            ),
        )


class TestContactsListConfig(unittest.TestCase):
    def test_an_empty_section_takes_the_defaults(self):
        # YAML's `contacts_list:` with nothing under it is None
        service = _LookupService({'contacts_list': None}, FakeSourceManager({}), Mock())
        self.addCleanup(service.stop)

        assert_that(service._list_timeout, equal_to(10))
        assert_that(
            service._list_cache.ttl if service._list_cache else None, equal_to(30)
        )
        assert_that(
            service._list_cache.max_contacts if service._list_cache else None,
            equal_to(100000),
        )
