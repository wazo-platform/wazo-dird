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
from hamcrest import not_
from hamcrest import none
from mock import Mock
from mock import patch
from mock import sentinel as s
from xivo_dird.plugins.favorites_service import FavoritesServicePlugin
from xivo_dird.plugins.favorites_service import _FavoritesService


class TestFavoritesServicePlugin(unittest.TestCase):

    def test_load_no_config(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': s.sources})

    def test_load_no_sources(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': s.sources})

    def test_that_load_returns_a_service(self):
        plugin = FavoritesServicePlugin()

        service = plugin.load({'sources': s.sources,
                               'config': s.config})

        assert_that(service, not_(none()))

    @patch('xivo_dird.plugins.favorites_service._FavoritesService')
    def test_that_load_injects_config_to_the_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        service = plugin.load({'config': s.config,
                               'sources': s.sources})

        MockedFavoritesService.assert_called_once_with(s.config, s.sources)
        assert_that(service, equal_to(MockedFavoritesService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = FavoritesServicePlugin()

        plugin.unload()

    @patch('xivo_dird.plugins.favorites_service._FavoritesService')
    def test_that_unload_stops_the_services(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()
        plugin.load({'config': s.config, 'sources': s.sources})

        plugin.unload()

        MockedFavoritesService.return_value.stop.assert_called_once_with()


class TestFavoritesService(unittest.TestCase):

    @patch('xivo_dird.plugins.favorites_service.Consul')
    def test_that_list_favorites_passes_down_token_infos(self, consul):
        consul_mock = consul.return_value
        consul_mock.kv.get.return_value = (None, [])
        source = Mock(list=Mock(return_value=[{'f': 1}]))
        source.name = 'source'
        config = {
            'services': {
                'favorites': {
                    'my_profile': {
                        'sources': ['source']
                    }
                }
            },
            'consul': {
                'host': 'localhost'
            }
        }
        service = _FavoritesService(config, {'source': source})
        token_infos = {'token': s.token, 'auth_id': s.auth_id}

        service.favorites('my_profile', token_infos)

        source.list.assert_called_once_with([],
                                            {'token_infos': token_infos})

        service.stop()

    @patch('xivo_dird.plugins.favorites_service.Consul')
    def test_that_favorites_searches_only_the_configured_sources(self, consul):
        consul_mock = consul.return_value
        consul_mock.kv.get.return_value = (None, [])
        sources = {
            'source_1': Mock(list=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(list=Mock(return_value=[{'f': 2}])),
            'source_3': Mock(list=Mock(return_value=[{'f': 3}])),
        }
        for source_name in sources:  # workaround mock.name that can't be set in __init__
            sources[source_name].name = source_name
        config = {
            'services': {
                'favorites': {
                    'my_profile': {
                        'sources': ['source_1', 'source_3'],
                        'timeout': '1',
                    }
                }
            },
            'consul': {
                'host': 'localhost'
            }
        }

        service = _FavoritesService(config, sources)

        results = service.favorites('my_profile', {'token': s.token, 'auth_id': s.auth_id})

        expected_results = [{'f': 1}, {'f': 3}]

        assert_that(sources['source_1'].list.call_count, equal_to(1))
        assert_that(sources['source_2'].list.call_count, equal_to(0))
        assert_that(sources['source_3'].list.call_count, equal_to(1))

        assert_that(results, contains_inanyorder(*expected_results))

        service.stop()

    @patch('xivo_dird.plugins.favorites_service.Consul')
    def test_that_favorites_does_not_fail_if_one_config_is_not_correct(self, consul):
        consul_mock = consul.return_value
        consul_mock.kv.get.return_value = (None, [])
        sources = {
            'source_1': Mock(name='source_1', list=Mock(return_value=[{'f': 1}])),
            'source_2': Mock(name='source_2', list=Mock(return_value=[{'f': 2}])),
            # 'source_3': Mock(name='source_3', list=Mock(return_value=[{'f': 3}])),  # ERROR in yaml config
        }
        for source_name in sources:  # workaround mock.name that can't be set in __init__
            sources[source_name].name = source_name
        config = {
            'services': {
                'favorites': {
                    'my_profile': {
                        'sources': ['source_1', 'source_3'],
                        'timeout': '1',
                    }
                }
            },
            'consul': {
                'host': 'localhost'
            }
        }

        service = _FavoritesService(config, sources)

        results = service.favorites('my_profile', {'token': s.token, 'auth_id': s.auth_id})

        expected_results = [{'f': 1}]

        assert_that(sources['source_1'].list.call_count, equal_to(1))
        assert_that(sources['source_2'].list.call_count, equal_to(0))

        assert_that(results, contains_inanyorder(*expected_results))

        service.stop()

    def test_when_the_profile_is_not_configured(self):
        service = _FavoritesService({}, {})

        result = service.favorites('my_profile', token_infos={})

        assert_that(result, contains())

        service.stop()

    def test_when_the_sources_are_not_configured(self):
        service = _FavoritesService({'my_profile': {}}, {})

        result = service.favorites('my_profile', token_infos={})

        assert_that(result, contains())

        service.stop()

    @patch('xivo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _FavoritesService({}, {})

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('xivo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        service = _FavoritesService({}, {})

        service.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()

    @patch('xivo_dird.plugins.favorites_service.Consul')
    def test_that_favorites_are_listed_in_each_source_with_the_right_id_list(self, consul_init):
        consul = consul_init.return_value
        sources = {
            'source_1': Mock(list=Mock(return_value=['contact1'])),
            'source_2': Mock(list=Mock(return_value=['contact2'])),
        }
        for source_name in sources:  # workaround mock.name that can't be set in __init__
            sources[source_name].name = source_name
        config = {
            'services': {
                'favorites': {
                    'my_profile': {
                        'sources': ['source_1', 'source_2'],
                        'timeout': '1',
                    }
                }
            },
            'consul': {
                'host': 'localhost'
            }
        }
        consul.kv.get.side_effect = [
            (Mock(), ['xivo/private/uuid/contacts/favorites/{source}/id1']),
            (Mock(), ['xivo/private/uuid/contacts/favorites/{source}/id2']),
        ]
        service = _FavoritesService(config, sources)

        token_infos = {'token': s.token, 'auth_id': 'uuid'}
        result = service.favorites('my_profile', token_infos)

        sources['source_1'].list.assert_called_once_with(['id1'], {'token_infos': token_infos})
        sources['source_2'].list.assert_called_once_with(['id2'], {'token_infos': token_infos})
        assert_that(result, contains_inanyorder('contact1', 'contact2'))

        service.stop()

    @patch('xivo_dird.plugins.favorites_service.Consul')
    def test_that_removing_unknown_favorites_raises_error(self, consul_init):
        consul_init.return_value.kv.get.return_value = (None, None)
        service = _FavoritesService({'consul': {'host': 'localhost'}}, {})

        self.assertRaises(service.NoSuchFavorite, service.remove_favorite,
                          'unknown_source', 'unknown_contact', {'token': s.token, 'auth_id': s.auth_id})

        service.stop()
