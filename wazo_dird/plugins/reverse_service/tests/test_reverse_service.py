# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import time
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

from ..plugin import (
    ReverseServicePlugin,
    _ReverseService,
)


class TestReverseServicePlugin(unittest.TestCase):

    def setUp(self):
        self._source_manager = Mock()

    def test_load_no_config(self):
        plugin = ReverseServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': sentinel.sources})

    def test_load_no_sources(self):
        plugin = ReverseServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': sentinel.sources})

    def test_that_load_returns_a_service(self):
        plugin = ReverseServicePlugin()

        service = plugin.load({'source_manager': self._source_manager,
                               'config': sentinel.config})

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.reverse_service.plugin._ReverseService')
    def test_that_load_injects_config_to_the_service(self, MockedReverseService):
        plugin = ReverseServicePlugin()

        service = plugin.load({'config': sentinel.config,
                               'source_manager': self._source_manager})

        MockedReverseService.assert_called_once_with(sentinel.config, self._source_manager)
        assert_that(service, equal_to(MockedReverseService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = ReverseServicePlugin()

        plugin.unload()

    @patch('wazo_dird.plugins.reverse_service.plugin._ReverseService')
    def test_that_unload_stops_the_services(self, MockedReverseService):
        plugin = ReverseServicePlugin()
        plugin.load({'config': sentinel.config, 'source_manager': self._source_manager})

        plugin.unload()

        MockedReverseService.return_value.stop.assert_called_once_with()


class TestReverseService(unittest.TestCase):

    def test_that_reverse_passes_down_infos(self):
        source = Mock(first_match=Mock(return_value=[{'f': 1}]))
        config = {
            'services': {
                'reverse': {
                    'my_profile': {
                        'sources': {'source': True}
                    }
                }
            }
        }
        s = _ReverseService(config, {'source': source})

        s.reverse(sentinel.exten, 'my_profile', {}, sentinel.uuid, sentinel.token)

        source.first_match.assert_called_once_with(sentinel.exten,
                                                   {'token': sentinel.token, 'xivo_user_uuid': sentinel.uuid})

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
                        'sources': {'source_1': True, 'source_3': True},
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

    def test_that_reverse_first_match_return_none_when_timeout_reached(self):
        source = Mock(first_match=Mock(side_effect=lambda x, y: time.sleep(0.1)))
        config = {
            'services': {
                'reverse': {
                    'my_profile': {
                        'sources': {'source': True},
                        'timeout': 0.0001
                    }
                }
            }
        }
        s = _ReverseService(config, {'source': source})

        result = s.reverse(sentinel.exten, 'my_profile', {}, sentinel.uuid, sentinel.token)

        assert_that(result, is_(none()))

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
                        'sources': {'source_1': True, 'source_3': True},
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

    @patch('wazo_dird.plugins.reverse_service.plugin.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _ReverseService({}, {})

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('wazo_dird.plugins.reverse_service.plugin.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        s = _ReverseService({}, {})

        s.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()
