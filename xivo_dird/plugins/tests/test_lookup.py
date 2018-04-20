# -*- coding: utf-8 -*-
# Copyright 2014-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import not_
from hamcrest import none
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird.plugins.lookup import LookupServicePlugin
from xivo_dird.plugins.lookup import _LookupService


class TestLookupServicePlugin(unittest.TestCase):

    def test_load_no_config(self):
        plugin = LookupServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': sentinel.sources})

    def test_load_no_sources(self):
        plugin = LookupServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': sentinel.sources})

    def test_that_load_returns_a_service(self):
        plugin = LookupServicePlugin()

        service = plugin.load({'sources': sentinel.sources,
                               'config': sentinel.config})

        assert_that(service, not_(none()))

    @patch('xivo_dird.plugins.lookup._LookupService')
    def test_that_load_injects_config_to_the_service(self, MockedLookupService):
        plugin = LookupServicePlugin()

        service = plugin.load({'config': sentinel.config,
                               'sources': sentinel.sources})

        MockedLookupService.assert_called_once_with(sentinel.config, sentinel.sources)
        assert_that(service, equal_to(MockedLookupService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = LookupServicePlugin()

        plugin.unload()

    @patch('xivo_dird.plugins.lookup._LookupService')
    def test_that_unload_stops_the_services(self, MockedLookupService):
        plugin = LookupServicePlugin()
        plugin.load({'config': sentinel.config, 'sources': sentinel.sources})

        plugin.unload()

        MockedLookupService.return_value.stop.assert_called_once_with()


class TestLookupService(unittest.TestCase):

    def test_that_lookup_passes_down_token_infos(self):
        source = Mock(search=Mock(return_value=[{'f': 1}]))
        config = {
            'services': {
                'lookup': {
                    'my_profile': {
                        'sources': {'source': True}
                    }
                }
            }
        }
        s = _LookupService(config, {'source': source})

        s.lookup(sentinel.term, 'my_profile', sentinel.uuid, {}, sentinel.token)

        source.search.assert_called_once_with(sentinel.term,
                                              {'token': sentinel.token,
                                               'xivo_user_uuid': sentinel.uuid})

        s.stop()

    def test_that_lookup_searches_only_the_configured_sources(self):
        sources = {
            'source_1': Mock(name='source_1', search=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(name='source_2', search=Mock(return_value=[{'f': 2}])),
            'source_3': Mock(name='source_3', search=Mock(return_value=[{'f': 3}])),
        }
        config = {
            'services': {
                'lookup': {
                    'my_profile': {
                        'sources': {'source_1': True, 'source_3': True},
                        'timeout': 1,
                    }
                }
            }
        }

        s = _LookupService(config, sources)

        results = s.lookup(sentinel.term, 'my_profile', sentinel.uuid, {}, sentinel.token)

        expected_results = [{'f': 1}, {'f': 3}]

        assert_that(sources['source_1'].search.call_count, equal_to(1))
        assert_that(sources['source_2'].search.call_count, equal_to(0))
        assert_that(sources['source_3'].search.call_count, equal_to(1))

        assert_that(results, contains_inanyorder(*expected_results))

        s.stop()

    def test_that_lookup_does_not_fail_if_one_config_is_not_correct(self):
        sources = {
            'source_1': Mock(name='source_1', search=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(name='source_2', search=Mock(return_value=[{'f': 2}])),
            # 'source_3': Mock(name='source_3', search=Mock(return_value=[{'f': 3}])),  # ERROR in yaml config
        }
        config = {
            'services': {
                'lookup': {
                    'my_profile': {
                        'sources': {'source_1': True, 'source_3': True},
                        'timeout': 1,
                    }
                }
            }
        }

        s = _LookupService(config, sources)

        results = s.lookup(sentinel.term, 'my_profile', sentinel.uuid, {}, sentinel.token)

        expected_results = [{'f': 1}]

        assert_that(sources['source_1'].search.call_count, equal_to(1))
        assert_that(sources['source_2'].search.call_count, equal_to(0))

        assert_that(results, contains_inanyorder(*expected_results))

        s.stop()

    def test_when_the_profile_is_not_configured(self):
        s = _LookupService({}, {})

        result = s.lookup(sentinel.term, 'my_profile', sentinel.uuid, {}, sentinel.token)

        assert_that(result, contains())

        s.stop()

    def test_when_the_sources_are_not_configured(self):
        s = _LookupService({'my_profile': {}}, {})

        result = s.lookup(sentinel.term, 'my_profile', sentinel.uuid, {}, sentinel.token)

        assert_that(result, contains())

        s.stop()

    @patch('xivo_dird.plugins.lookup.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _LookupService({}, {})

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('xivo_dird.plugins.lookup.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        s = _LookupService({}, {})

        s.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()
