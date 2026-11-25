# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import unittest
from typing import cast
from unittest.mock import ANY, Mock, sentinel

import ldap
from hamcrest import assert_that, calling, contains_exactly, equal_to, raises
from ldap.controls import SimplePagedResultsControl
from ldap.ldapobject import LDAPObject

from wazo_dird.exception import SourceListError
from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import (
    LDAPPlugin,
    _LDAPClient,
    _LDAPConfig,
    _LDAPFactory,
    _LDAPResultFormatter,
)

BASE_DN = 'ou=people,dc=foobar'
ATTRIBUTES = ['entryUUID', 'givenName']


def _page_control(cookie):
    return SimplePagedResultsControl(True, size=500, cookie=cookie)


class _ClientCase(unittest.TestCase):
    def setUp(self):
        self.ldap_config = Mock(_LDAPConfig)
        self.ldap_config.ldap_uri.return_value = 'ldap://example.org'
        self.ldap_config.ldap_base_dn.return_value = BASE_DN
        self.ldap_config.attributes.return_value = ATTRIBUTES
        self.ldap_config.name.return_value = 'my-ldap'
        self.ldap_obj = Mock(LDAPObject)
        self.ldap_obj_factory = Mock(return_value=self.ldap_obj)
        self.client = _LDAPClient(self.ldap_config, self.ldap_obj_factory)


class TestLDAPClientSearchAll(_ClientCase):
    def test_search_all_reads_every_page(self):
        self.ldap_obj.search_ext.side_effect = [1, 2, 3]
        self.ldap_obj.result3.side_effect = [
            (ANY, [('cn=a', {}), ('cn=b', {})], 1, [_page_control(b'p2')]),
            (ANY, [('cn=c', {})], 2, [_page_control(b'p3')]),
            (ANY, [('cn=d', {})], 3, [_page_control(b'')]),
        ]

        results = self.client.search_all('(objectClass=*)')

        assert_that(
            [dn for dn, _ in results],
            contains_exactly('cn=a', 'cn=b', 'cn=c', 'cn=d'),
        )
        calls = self.ldap_obj.search_ext.call_args_list
        assert_that(len(calls), equal_to(3))
        for call_ in calls:
            assert_that(
                call_.args,
                equal_to((BASE_DN, ldap.SCOPE_SUBTREE, '(objectClass=*)', ATTRIBUTES)),
            )
        cookies = [c.kwargs['serverctrls'][0].cookie for c in calls]
        assert_that(cookies, equal_to(['', b'p2', b'p3']))

    def test_search_all_stops_when_the_server_sends_no_page_control(self):
        self.ldap_obj.search_ext.return_value = 1
        self.ldap_obj.result3.return_value = (ANY, [('cn=a', {})], 1, [])

        results = self.client.search_all('(objectClass=*)')

        assert_that(results, equal_to([('cn=a', {})]))
        assert_that(self.ldap_obj.search_ext.call_count, equal_to(1))

    def test_search_all_raises_on_an_ldap_error(self):
        for error in (ldap.SERVER_DOWN('down'), ldap.SIZELIMIT_EXCEEDED('limit')):
            self.ldap_obj.search_ext.side_effect = error

            assert_that(
                calling(self.client.search_all).with_args('(objectClass=*)'),
                raises(SourceListError),
            )

    def test_search_all_raises_when_the_bind_fails(self):
        self.ldap_obj.simple_bind_s.side_effect = ldap.INVALID_CREDENTIALS('no')

        assert_that(
            calling(self.client.search_all).with_args('(objectClass=*)'),
            raises(SourceListError),
        )
        self.ldap_obj.search_ext.assert_not_called()


class TestLDAPPluginListAll(unittest.TestCase):
    def setUp(self):
        self.ldap_config = Mock(_LDAPConfig)
        self.formatter = Mock(_LDAPResultFormatter)
        self.search_client = Mock(_LDAPClient)
        self.list_client = Mock(_LDAPClient)
        self.ldap_factory = Mock(_LDAPFactory)
        self.ldap_factory.new_ldap_config.return_value = self.ldap_config
        self.ldap_factory.new_ldap_result_formatter.return_value = self.formatter
        self.ldap_factory.new_ldap_client.side_effect = [
            self.search_client,
            self.list_client,
        ]
        self.plugin = LDAPPlugin()
        self.plugin.ldap_factory = self.ldap_factory
        self.plugin.load(cast(SourcePluginDependencies, {'config': sentinel}))

    def test_list_all_lists_every_entry_on_its_own_connection(self):
        self.list_client.search_all.return_value = sentinel.raw
        self.formatter.format.return_value = sentinel.formatted

        result = self.plugin.list_all()

        self.list_client.search_all.assert_called_once_with('(objectClass=*)')
        self.search_client.search.assert_not_called()
        self.ldap_config.build_search_filter.assert_not_called()
        self.formatter.format.assert_called_once_with(sentinel.raw)
        assert_that(result, equal_to(sentinel.formatted))

    def test_list_all_propagates_a_list_error(self):
        self.list_client.search_all.side_effect = SourceListError('my-ldap')

        assert_that(calling(self.plugin.list_all), raises(SourceListError))

    def test_unload_closes_both_connections(self):
        self.list_client.search_all.return_value = []
        self.plugin.list_all()

        self.plugin.unload()

        self.search_client.close.assert_called_once_with()
        self.list_client.close.assert_called_once_with()

    def test_a_reverse_lookup_answers_while_a_listing_is_in_progress(self):
        listing = threading.Event()
        release = threading.Event()

        def slow_search_all(filter_str):
            listing.set()
            release.wait(5)
            return []

        self.list_client.search_all.side_effect = slow_search_all
        self.search_client.search.return_value = [('cn=a', {'cn': [b'a']})]
        self.formatter.format_one_result.return_value = sentinel.reverse
        lister = threading.Thread(target=self.plugin.list_all)
        answers = []
        reverse = threading.Thread(
            target=lambda: answers.append(self.plugin.first_match('a'))
        )
        try:
            lister.start()
            listing.wait(5)
            reverse.start()
            reverse.join(1)

            assert_that(answers, contains_exactly(sentinel.reverse))
            assert_that(lister.is_alive(), equal_to(True))
        finally:
            release.set()
            lister.join(5)
            reverse.join(5)


class TestLDAPClientSearchAllReconnects(_ClientCase):
    def test_search_all_reconnects_once_on_a_dropped_connection(self):
        self.client.set_up()
        self.ldap_obj.search_ext.side_effect = [ldap.SERVER_DOWN('restarted'), 7]
        self.ldap_obj.result3.return_value = (ANY, [('cn=a', {})], 7, [])

        results = self.client.search_all('(objectClass=*)')

        assert_that(results, equal_to([('cn=a', {})]))
        assert_that(self.ldap_obj_factory.call_count, equal_to(2))

    def test_search_all_raises_when_the_reconnection_fails_too(self):
        self.client.set_up()
        self.ldap_obj.search_ext.side_effect = ldap.SERVER_DOWN('down')

        assert_that(
            calling(self.client.search_all).with_args('(objectClass=*)'),
            raises(SourceListError),
        )
        assert_that(self.ldap_obj.search_ext.call_count, equal_to(2))

    def test_a_failing_unbind_still_raises_a_list_error(self):
        self.client.set_up()
        self.ldap_obj.search_ext.side_effect = ldap.SERVER_DOWN('down')
        self.ldap_obj.unbind_s.side_effect = ldap.SERVER_DOWN('down')

        assert_that(
            calling(self.client.search_all).with_args('(objectClass=*)'),
            raises(SourceListError),
        )
