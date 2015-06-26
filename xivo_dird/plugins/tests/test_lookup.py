# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird import BaseService
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

        assert_that(isinstance(service, BaseService))

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
                        'sources': ['source_1', 'source_3'],
                        'timeout': '1',
                    }
                }
            }
        }

        s = _LookupService(config, sources)

        results = s(sentinel.term, 'my_profile', sentinel.args)

        expected_results = [{'f': 1}, {'f': 3}]

        sources['source_1'].search.assert_called_once_with(sentinel.term, 'my_profile', sentinel.args)
        assert_that(sources['source_2'].call_count, equal_to(0))
        sources['source_3'].search.assert_called_once_with(sentinel.term, 'my_profile', sentinel.args)

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
                        'sources': ['source_1', 'source_3'],
                        'timeout': '1',
                    }
                }
            }
        }

        s = _LookupService(config, sources)

        results = s(sentinel.term, 'my_profile', sentinel.args)

        expected_results = [{'f': 1}]

        sources['source_1'].search.assert_called_once_with(sentinel.term, 'my_profile', sentinel.args)
        assert_that(sources['source_2'].call_count, equal_to(0))

        assert_that(results, contains_inanyorder(*expected_results))

        s.stop()

    def test_when_the_profile_is_not_configured(self):
        s = _LookupService({}, {})

        result = s(sentinel.term, 'my_profile', sentinel.args)

        assert_that(result, contains())

        s.stop()

    def test_when_the_sources_are_not_configured(self):
        s = _LookupService({'my_profile': {}}, {})

        result = s(sentinel.term, 'my_profile', sentinel.args)

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
