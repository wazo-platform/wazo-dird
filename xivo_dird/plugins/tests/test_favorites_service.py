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
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from mock import Mock
from mock import patch
from mock import sentinel
from xivo_dird import BaseService
from xivo_dird.plugins.favorites_service import FavoritesServicePlugin
from xivo_dird.plugins.favorites_service import _FavoritesService
from xivo_dird.plugins.favorites_service import NoSuchFavorite


class TestFavoritesServicePlugin(unittest.TestCase):

    def test_load_no_config(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': sentinel.sources})

    def test_load_no_sources(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': sentinel.sources})

    def test_that_load_returns_a_service(self):
        plugin = FavoritesServicePlugin()

        service = plugin.load({'sources': sentinel.sources,
                               'config': sentinel.config})

        assert_that(isinstance(service, BaseService))

    @patch('xivo_dird.plugins.favorites_service._FavoritesService')
    def test_that_load_injects_config_to_the_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        service = plugin.load({'config': sentinel.config,
                               'sources': sentinel.sources})

        MockedFavoritesService.assert_called_once_with(sentinel.config, sentinel.sources)
        assert_that(service, equal_to(MockedFavoritesService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = FavoritesServicePlugin()

        plugin.unload()

    @patch('xivo_dird.plugins.favorites_service._FavoritesService')
    def test_that_unload_stops_the_services(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()
        plugin.load({'config': sentinel.config, 'sources': sentinel.sources})

        plugin.unload()

        MockedFavoritesService.return_value.stop.assert_called_once_with()


class TestFavoritesService(unittest.TestCase):

    def test_that_favorites_searches_only_the_configured_sources(self):
        sources = {
            'source_1': Mock(name='source_1', list=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(name='source_2', list=Mock(return_value=[{'f': 2}])),
            'source_3': Mock(name='source_3', list=Mock(return_value=[{'f': 3}])),
        }
        config = {
            'my_profile': {
                'sources': ['source_1', 'source_3'],
                'timeout': '1',
            }
        }

        s = _FavoritesService(config, sources)

        results = s('my_profile')

        expected_results = [{'f': 1}, {'f': 3}]

        sources['source_1'].list.assert_called_once_with([])
        assert_that(sources['source_2'].call_count, equal_to(0))
        sources['source_3'].list.assert_called_once_with([])

        assert_that(results, contains_inanyorder(*expected_results))

        s.stop()

    def test_that_favorites_does_not_fail_if_one_config_is_not_correct(self):
        sources = {
            'source_1': Mock(name='source_1', list=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(name='source_2', list=Mock(return_value=[{'f': 2}])),
            # 'source_3': Mock(name='source_3', list=Mock(return_value=[{'f': 3}])),  # ERROR in yaml config
        }
        config = {
            'my_profile': {
                'sources': ['source_1', 'source_3'],
                'timeout': '1',
            }
        }

        s = _FavoritesService(config, sources)

        results = s('my_profile')

        expected_results = [{'f': 1}]

        sources['source_1'].list.assert_called_once_with([])
        assert_that(sources['source_2'].call_count, equal_to(0))

        assert_that(results, contains_inanyorder(*expected_results))

        s.stop()

    def test_when_the_profile_is_not_configured(self):
        s = _FavoritesService({}, {})

        result = s('my_profile')

        assert_that(result, contains())

        s.stop()

    def test_when_the_sources_are_not_configured(self):
        s = _FavoritesService({'my_profile': {}}, {})

        result = s('my_profile')

        assert_that(result, contains())

        s.stop()

    @patch('xivo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _FavoritesService({}, {})

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('xivo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        s = _FavoritesService({}, {})

        s.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()

    def test_that_favorites_are_listed_on_the_right_source(self):
        sources = {
            'source_1': Mock(list=Mock(return_value=['contact1'])),
            'source_2': Mock(list=Mock(return_value=['contact2'])),
        }
        # Not settable via Mock constructor
        sources['source_1'].name = 'source_1'
        sources['source_2'].name = 'source_2'
        config = {
            'my_profile': {
                'sources': ['source_1', 'source_2'],
                'timeout': '1',
            }
        }
        s = _FavoritesService(config, sources)
        s.new_favorite('source_1', 'id1')
        s.new_favorite('source_2', 'id2')

        result = s.favorites('my_profile')

        sources['source_1'].list.assert_called_once_with(['id1'])
        sources['source_2'].list.assert_called_once_with(['id2'])
        assert_that(result, contains_inanyorder('contact1', 'contact2'))

        s.stop()

    def test_that_removing_unknown_favorites_raises_error(self):
        s = _FavoritesService({}, {})

        self.assertRaises(NoSuchFavorite, s.remove_favorite, 'source_unknown', 'id')

        s.stop()

    def test_that_removed_favorites_are_not_listed_anymore(self):
        sources = {
            'source_1': Mock(list=Mock(return_value=[])),
        }
        # Not settable via Mock constructor
        sources['source_1'].name = 'source_1'
        config = {
            'my_profile': {
                'sources': ['source_1'],
                'timeout': '1',
            }
        }
        s = _FavoritesService(config, sources)
        s.new_favorite('source_1', 'id1')
        s.remove_favorite('source_1', 'id1')

        result = s.favorites('my_profile')

        sources['source_1'].list.assert_called_once_with([])
        assert_that(result, contains())

        s.stop()
