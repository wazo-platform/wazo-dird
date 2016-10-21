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

from hamcrest import assert_that, equal_to
from mock import Mock, patch

from ..service_discovery_service import ConfigUpdater


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
  version: 1.1
format_columns:
    number: "{exten}"
    reverse: "{firstname} {lastname}"
    voicemail: "{voicemail_number}"
'''


class TestServiceDiscoveryServicePlugin(unittest.TestCase):
    pass


class TestServiceDiscoveryService(unittest.TestCase):

    def test_that_the_service_looks_for_remote_servers_when_starting(self):
        pass


class TestConfigUpdater(unittest.TestCase):

    def setUp(self):
        self.template_file = tempfile.NamedTemporaryFile()
        with open(self.template_file.name, 'w') as f:
            f.write(TEMPLATE)
        self.template_dir, self.template_filename = os.path.split(self.template_file.name)
        self.config = {
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
                    'template_path': self.template_dir,
                    'services': {
                        'xivo-confd': {
                            'template': self.template_filename,
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

    def tearDown(self):
        try:
            os.unlink(self.template_file.name)
        except IOError:
            return

    def test_that_on_service_added_modifies_the_config(self):
        updater = ConfigUpdater(self.config)

        new_service_msg = {
            'service': 'xivo-confd',
            'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
            'port': 9487,
            'hostname': 'remote',
        }

        source_name = 'xivo-ff791b0e-3d28-4b4d-bb90-2724c0a248cb'
        with patch.object(updater,
                          'build_source_config',
                          Mock(return_value={'name': source_name})):
            updater.on_service_added(new_service_msg)

        expected_lookup_service = {
            'foobar': {'sources': ['source_1', 'source_2', source_name]},
            'default': {'sources': ['source_2', source_name]}}
        expected_reverse_service = {
            'foobar': {'sources': ['source_1', 'source_2', source_name]},
            'default': {'sources': ['source_2']},
            '__switchboard': {'sources': [source_name]}}
        expected_favorites_service = {
            'foobar': {'sources': ['source_2', source_name]},
            'default': {'sources': ['source_2', source_name]}}

        assert_that(self.config['services']['lookup'],
                    equal_to(expected_lookup_service))
        assert_that(self.config['services']['reverse'],
                    equal_to(expected_reverse_service))
        assert_that(self.config['services']['favorites'],
                    equal_to(expected_favorites_service))

    def test_that_an_unconfigured_consul_service_does_nothing(self):
        original_config = dict(self.config)

        updater = ConfigUpdater(self.config)

        new_service_msg = {
            'service': 'xivo-ctid',
            'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb',
            'port': 9495,
            'hostname': 'remote',
        }

        updater.on_service_added(new_service_msg)

        assert_that(self.config, equal_to(original_config))

    def test_that_a_consul_service_with_an_unknown_uuid_does_nothing(self):
        original_config = dict(self.config)

        updater = ConfigUpdater(self.config)

        new_service_msg = {
            'service': 'xivo-confd',
            'uuid': 'ff791b0e-3d28-4b4d-bb90-2724c0a24NOT',
            'port': 9495,
            'hostname': 'remote',
        }

        updater.on_service_added(new_service_msg)

        assert_that(self.config, equal_to(original_config))

    def test_build_source_config(self):
        uuid = 'ff791b0e-3d28-4b4d-bb90-2724c0a248cb'
        msg = {
            'service': 'xivo-confd',
            'uuid': uuid,
            'port': 9495,
            'hostname': 'remote',
        }
        host_config = self.config['services']['service_discovery']['hosts'][uuid]
        updater = ConfigUpdater(self.config)

        source_config = updater.build_source_config(self.template_filename,
                                                    msg,
                                                    host_config)

        expected_config = {
            'type': 'xivo',
            'name': 'xivo-{}'.format(uuid),
            'searched_columns': ['firstname', 'lastname'],
            'first_matched_columns': ['exten'],
            'confd_config': {
                'host': 'remote',
                'port': 9495,
                'version': 1.1,
            },
            'format_columns': {
                'number': '{exten}',
                'reverse': '{firstname} {lastname}',
                'voicemail': '{voicemail_number}',
            }
        }
        assert_that(source_config, equal_to(expected_config))
