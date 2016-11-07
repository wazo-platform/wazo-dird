# -*- coding: utf-8 -*-

# Copyright (C) 2016 Proformatique, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import os
import tempfile
import unittest

from hamcrest import assert_that, equal_to, not_
from mock import sentinel as s

from ..service_discovery_service import (
    ProfileConfigUpdater,
    SourceConfigGenerator,
    SourceConfigManager,
)


TEMPLATE = '''\
type: xivo
name: xivo-{{ uuid }}
searched_columns:
  - firstname
  - lastname
first_matched_columns:
  - exten
confd_config:
  host: {{ hostname }}
  port: {{ port }}
  version: "1.1"
format_columns:
    number: "{exten}"
    reverse: "{firstname} {lastname}"
    voicemail: "{voicemail_number}"
'''

CONFIG = {
    'services': {
        'lookup': {
            'foobar': {'sources': ['source_1', 'source_2']},
            'default': {'sources': ['source_2']},
        },
        'reverse': {
            'foobar': {'sources': ['source_1', 'source_2']},
            'default': {'sources': ['source_2']},
        },
        'favorites': {
            'foobar': {'sources': ['source_2']},
            'default': {'sources': ['source_2']},
        },
        'service_discovery': {
            'template_path': None,
            'services': {
                'xivo-confd': {
                    'template': None,
                    'lookup': {
                        'foobar': True,
                        'default': True,
                        '__switchboard': False,
                    },
                    'reverse': {
                        'foobar': True,
                        'default': False,
                        '__switchboard': True,
                    },
                    'favorites': {
                        'foobar': True,
                        'default': True,
                        '__switboard': False,
                    },
                },
            },
            'hosts': {
                'ff791b0e-3d28-4b4d-bb90-2724c0a248cb': {
                    'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        },
    },
}


class TestServiceDiscoveryServicePlugin(unittest.TestCase):
    pass


class TestServiceDiscoveryService(unittest.TestCase):

    def test_that_the_service_looks_for_remote_servers_when_starting(self):
        pass


def new_template_file(content):
    f = tempfile.NamedTemporaryFile(delete=False)
    with open(f.name, 'w') as f:
        f.write(content)
    dir_, name = os.path.split(f.name)
    return f, dir_, name


class TestSourceConfigManager(unittest.TestCase):

    def setUp(self):
        self.source_config = {
            "personal": {
                "name": "personal",
                "type": "personal",
            },
            "xivodir": {
                "name": "xivodir",
                "type": "dird_phonebook",
            },
            None: {
                "name": None,
                "type": "invalid",
            },
        }

    def test_source_exists(self):
        manager = SourceConfigManager(self.source_config)

        assert_that(manager.source_exists('personal'))
        assert_that(not_(manager.source_exists('foobar')))
        assert_that(not_(manager.source_exists(None)))

    def test_add_source(self):
        manager = SourceConfigManager(self.source_config)

        foobar_config = {'name': 'foobar',
                         'type': 'dird_phonebook'}

        manager.add_source(foobar_config)

        assert_that(self.source_config['foobar'], equal_to(foobar_config))


class TestSourceConfigGenerator(unittest.TestCase):

    def setUp(self):
        (self.template_file,
         self.template_dir,
         self.template_filename) = new_template_file(TEMPLATE)

    def tearDown(self):
        try:
            os.unlink(self.template_file.name)
        except OSError:
            return

    def test_generate_with_an_unknown_service(self):
        service_discovery_config = {
            'template_path': None,
            'services': {},
            'hosts': {
                'ff791b0e-3d28-4b4d-bb90-2724c0a248cb': {
                    'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        }

        generator = SourceConfigGenerator(service_discovery_config)

        config = generator.generate_from_new_service('unknown',
                                                     s.uuid,
                                                     s.host,
                                                     s.port)

        assert_that(config, equal_to(None))

    def test_generate_with_a_service(self):
        uuid = 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb'
        service_discovery_config = {
            'template_path': self.template_dir,
            'services': {
                'xivo-confd': {
                    'template': self.template_filename,
                },
            },
            'hosts': {
                uuid: {
                    'uuid': uuid,
                    'service_id': 'some-service-name',
                    'service_key': 'secre7',
                },
            },
        }

        generator = SourceConfigGenerator(service_discovery_config)

        config = generator.generate_from_new_service('xivo-confd',
                                                     uuid,
                                                     'the-host-name',
                                                     4567)
        expected = {
            'type': 'xivo',
            'name': 'xivo-ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['exten'],
            'confd_config': {
                'host': 'the-host-name',
                'port': 4567,
                'version': '1.1',
            },
            'format_columns': {
                'number': "{exten}",
                'reverse': "{firstname} {lastname}",
                'voicemail': "{voicemail_number}",
            },
        }

        assert_that(config, equal_to(expected))


class TestProfileConfigUpdater(unittest.TestCase):

    def setUp(self):
        self.config = dict(CONFIG)
        self.source_name = 'xivo-ff791b0e-3d28-4b4d-bb90-2724c0a248cb'

    def test_that_on_service_added_modifies_the_config(self):
        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-confd')

        expected_lookup_service = {
            'foobar': {'sources': ['source_1', 'source_2', self.source_name]},
            'default': {'sources': ['source_2', self.source_name]}}
        expected_reverse_service = {
            'foobar': {'sources': ['source_1', 'source_2', self.source_name]},
            'default': {'sources': ['source_2']},
            '__switchboard': {'sources': [self.source_name]}}
        expected_favorites_service = {
            'foobar': {'sources': ['source_2', self.source_name]},
            'default': {'sources': ['source_2', self.source_name]}}

        assert_that(self.config['services']['lookup'],
                    equal_to(expected_lookup_service))
        assert_that(self.config['services']['reverse'],
                    equal_to(expected_reverse_service))
        assert_that(self.config['services']['favorites'],
                    equal_to(expected_favorites_service))

    def test_that_an_unconfigured_consul_service_does_nothing(self):
        original_services = dict(self.config['services'])

        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-ctid')

        assert_that(self.config['services'], equal_to(original_services))

    def test_that_a_consul_service_with_an_unknown_uuid_does_nothing(self):
        original_services = dict(self.config['services'])

        updater = ProfileConfigUpdater(self.config)

        updater.on_service_added(self.source_name, 'xivo-confd')

        assert_that(self.config['services'], equal_to(original_services))
