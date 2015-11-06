# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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
from hamcrest import equal_to
from hamcrest import has_item
from hamcrest import is_
from hamcrest import none
from hamcrest import not_
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird.plugins.reverse_service import ReverseServicePlugin
from xivo_dird.plugins.reverse_service import _ReverseService


class TestReverseServicePlugin(unittest.TestCase):

    def test_load_no_config(self):
        plugin = ReverseServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': sentinel.sources})

    def test_load_no_sources(self):
        plugin = ReverseServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': sentinel.sources})

    def test_that_load_returns_a_service(self):
        plugin = ReverseServicePlugin()

        service = plugin.load({'sources': sentinel.sources,
                               'config': sentinel.config})

        assert_that(service, not_(none()))

    @patch('xivo_dird.plugins.reverse_service._ReverseService')
    def test_that_load_injects_config_to_the_service(self, MockedReverseService):
        plugin = ReverseServicePlugin()

        service = plugin.load({'config': sentinel.config,
                               'sources': sentinel.sources})

        MockedReverseService.assert_called_once_with(sentinel.config, sentinel.sources)
        assert_that(service, equal_to(MockedReverseService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = ReverseServicePlugin()

        plugin.unload()

    @patch('xivo_dird.plugins.reverse_service._ReverseService')
    def test_that_unload_stops_the_services(self, MockedReverseService):
        plugin = ReverseServicePlugin()
        plugin.load({'config': sentinel.config, 'sources': sentinel.sources})

        plugin.unload()

        MockedReverseService.return_value.stop.assert_called_once_with()


class TestReverseService(unittest.TestCase):

    def test_that_reverse_passes_down_infos(self):
        source = Mock(first_match=Mock(return_value=[{'f': 1}]))
        config = {
            'services': {
                'reverse': {
                    'my_profile': {
                        'sources': ['source']
                    }
                }
            }
        }
        s = _ReverseService(config, {'source': source})

        s.reverse(sentinel.exten, 'my_profile', {}, sentinel.uuid, sentinel.token)

        source.first_match.assert_called_once_with(sentinel.exten,
                                                   {'token': sentinel.token, 'auth_id': sentinel.uuid})

        s.stop()

    def test_that_reverse_first_match_only_the_configured_sources(self):
        sources = {
            'source_1': Mock(name='source_1', first_match=Mock(return_value={'f': 1})),
            'source_2': Mock(name='source_2', first_match=Mock(return_value={'f': 2})),
            'source_3': Mock(name='source_3', first_match=Mock(return_value={'f': 3})),
        }
        config = {
            'services': {
                'reverse': {
                    'my_profile': {
                        'sources': ['source_1', 'source_3'],
                        'timeout': 1,
                    }
                }
            }
        }

        s = _ReverseService(config, sources)

        result = s.reverse(sentinel.exten, 'my_profile', {}, sentinel.token_infos, sentinel.uuid)

        expected_result = [{'f': 1}, {'f': 3}]

        assert_that(sources['source_2'].first_match.call_count, equal_to(0))

        assert_that(expected_result, has_item(result))

        s.stop()

    def test_that_reverse_does_not_fail_if_one_config_is_not_correct(self):
        sources = {
            'source_1': Mock(name='source_1', first_match=Mock(return_value={'f': 1})),
            'source_2': Mock(name='source_2', first_match=Mock(return_value={'f': 2})),
            # 'source_3': Mock(name='source_3', first_match=Mock(return_value=['f': 3})),  # ERROR in yaml config
        }
        config = {
            'services': {
                'reverse': {
                    'my_profile': {
                        'sources': ['source_1', 'source_3'],
                        'timeout': 1,
                    }
                }
            }
        }

        s = _ReverseService(config, sources)

        result = s.reverse(sentinel.exten, 'my_profile', {}, sentinel.token_infos, sentinel.uuid)

        expected_result = {'f': 1}

        assert_that(sources['source_1'].first_match.call_count, equal_to(1))
        assert_that(sources['source_2'].first_match.call_count, equal_to(0))

        assert_that(result, equal_to(expected_result))

        s.stop()

    def test_when_the_profile_is_not_configured(self):
        s = _ReverseService({}, {})

        result = s.reverse(sentinel.exten, 'my_profile', {}, sentinel.token_infos, sentinel.uuid)

        assert_that(result, is_(none()))

        s.stop()

    def test_when_the_sources_are_not_configured(self):
        s = _ReverseService({'my_profile': {}}, {})

        result = s.reverse(sentinel.exten, 'my_profile', {}, sentinel.token_infos, sentinel.uuid)

        assert_that(result, is_(none()))

        s.stop()

    @patch('xivo_dird.plugins.reverse_service.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _ReverseService({}, {})

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('xivo_dird.plugins.reverse_service.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        s = _ReverseService({}, {})

        s.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()
