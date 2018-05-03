# -*- coding: utf-8 -*-
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest

from hamcrest import (assert_that,
                      calling,
                      contains,
                      contains_inanyorder,
                      equal_to,
                      not_,
                      none,
                      raises)
from mock import (ANY,
                  Mock,
                  patch,
                  sentinel as s)
from wazo_dird import database, bus
from wazo_dird.plugins.favorites_service import FavoritesServicePlugin
from wazo_dird.plugins.favorites_service import _FavoritesService


class TestFavoritesServicePlugin(unittest.TestCase):

    def setUp(self):
        self._config = {'db_uri': s.db_uri}

    def test_load_no_config(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'sources': s.sources})

    def test_load_no_sources(self):
        plugin = FavoritesServicePlugin()

        self.assertRaises(ValueError, plugin.load, {'config': self._config})

    def test_that_load_returns_a_service(self):
        plugin = FavoritesServicePlugin()

        with patch.object(plugin, '_new_favorite_crud'):
            service = plugin.load({'sources': s.sources,
                                   'config': self._config,
                                   'bus': s.bus})

        assert_that(service, not_(none()))

    @patch('wazo_dird.plugins.favorites_service._FavoritesService')
    def test_that_load_injects_config_to_the_service(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()

        with patch.object(plugin, '_new_favorite_crud'):
            service = plugin.load({'config': self._config,
                                   'sources': s.sources,
                                   'bus': s.bus})

        MockedFavoritesService.assert_called_once_with(self._config, s.sources, ANY, s.bus)
        assert_that(service, equal_to(MockedFavoritesService.return_value))

    def test_no_error_on_unload_not_loaded(self):
        plugin = FavoritesServicePlugin()

        plugin.unload()

    @patch('wazo_dird.plugins.favorites_service._FavoritesService')
    def test_that_unload_stops_the_services(self, MockedFavoritesService):
        plugin = FavoritesServicePlugin()
        with patch.object(plugin, '_new_favorite_crud'):
            plugin.load({'config': self._config,
                         'sources': s.sources,
                         'bus': s.bus})

        plugin.unload()

        MockedFavoritesService.return_value.stop.assert_called_once_with()


class TestFavoritesService(unittest.TestCase):

    def setUp(self):
        self.bus = Mock(bus.Bus)

    def test_that_unavailable_source_raises_404(self):
        config = {'services': {'favorites': {'my_profile': {'sources': ['one', 'two']}}}}
        sources = {'one': Mock(), 'two': Mock(), 'three': Mock()}
        crud = Mock(database.FavoriteCRUD)

        service = _FavoritesService(config, sources, crud, self.bus)

        assert_that(calling(service.new_favorite).with_args('three', 'the-id', s.xivo_user_uuid),
                    raises(service.NoSuchSourceException))
        assert_that(calling(service.remove_favorite).with_args('three', 'the-id', s.xivo_user_uuid),
                    raises(service.NoSuchSourceException))

    def test_that_favorites_searches_only_the_configured_sources(self):
        def get(self_):
            for ret in [('source_1', 'id1'),
                        ('source_3', 'id3')]:
                yield ret

        crud = Mock(database.FavoriteCRUD, get=get)
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
                        'sources': {'source_1': True, 'source_3': True},
                        'timeout': 1,
                    }
                }
            },
        }

        service = _FavoritesService(config, sources, crud, self.bus)

        results = service.favorites('my_profile', s.xivo_user_uuid)

        expected_results = [{'f': 1}, {'f': 3}]

        assert_that(sources['source_1'].list.call_count, equal_to(1))
        assert_that(sources['source_2'].list.call_count, equal_to(0))
        assert_that(sources['source_3'].list.call_count, equal_to(1))

        assert_that(results, contains_inanyorder(*expected_results))

        service.stop()

    def test_that_favorites_does_not_fail_if_one_config_is_not_correct(self):
        def get(self_):
            for ret in [('source_1', 'id1'),
                        ('source_2', 'id2')]:
                yield ret

        crud = Mock(database.FavoriteCRUD, get=get)
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
                        'sources': {'source_1': True, 'source_3': True},
                        'timeout': 1,
                    }
                }
            },
        }

        service = _FavoritesService(config, sources, crud, self.bus)

        results = service.favorites('my_profile', s.xivo_user_uuid)

        expected_results = [{'f': 1}]

        assert_that(sources['source_1'].list.call_count, equal_to(1))
        assert_that(sources['source_2'].list.call_count, equal_to(0))

        assert_that(results, contains_inanyorder(*expected_results))

        service.stop()

    def test_that_using_an_unconfigured_profile_raises(self):
        config = {'services': {'favorites': {'profile_1': {}}}}
        crud = Mock(database.FavoriteCRUD)
        sources = {}

        service = _FavoritesService(config, sources, crud, self.bus)

        assert_that(calling(service.favorites).with_args('my_profile', s.xivo_user_uuid),
                    raises(service.NoSuchProfileException))
        assert_that(calling(service.favorites).with_args('my_profile', s.xivo_user_uuid),
                    raises(service.NoSuchProfileException))

    def test_when_the_sources_are_not_configured(self):
        config = {'services': {'favorites': {'my_profile': {}}}}
        service = _FavoritesService(config, {}, Mock(get=Mock(return_value=[('source', 'id')])), self.bus)

        result = service.favorites('my_profile', s.xivo_user_uuid)

        assert_that(result, contains())

    @patch('wazo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_the_service_starts_the_thread_pool(self, MockedThreadPoolExecutor):
        _FavoritesService({}, {}, Mock(), self.bus)

        MockedThreadPoolExecutor.assert_called_once_with(max_workers=10)

    @patch('wazo_dird.plugins.favorites_service.ThreadPoolExecutor')
    def test_that_stop_shuts_down_the_thread_pool(self, MockedThreadPoolExecutor):
        service = _FavoritesService({}, {}, Mock(), self.bus)

        service.stop()

        MockedThreadPoolExecutor.return_value.shutdown.assert_called_once_with()

    def test_that_favorites_are_listed_in_each_source_with_the_right_id_list(self):
        def get(self_):
            for ret in [('source_1', 'id1'),
                        ('source_2', 'id2')]:
                yield ret

        crud = Mock(database.FavoriteCRUD, get=get)
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
                        'sources': {'source_1': True, 'source_2': True},
                        'timeout': 1,
                    }
                }
            },
        }
        service = _FavoritesService(config, sources, crud, self.bus)

        result = service.favorites('my_profile', s.xivo_user_uuid)

        args = {'token_infos': {'xivo_user_uuid': s.xivo_user_uuid}}
        sources['source_1'].list.assert_called_once_with(['id1'], args)
        sources['source_2'].list.assert_called_once_with(['id2'], args)
        assert_that(result, contains_inanyorder('contact1', 'contact2'))

        service.stop()
