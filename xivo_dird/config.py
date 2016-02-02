# -*- coding: utf-8 -*-

# Copyright (C) 2014-2016 Avencall
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

import argparse

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_dir, read_config_file_hierarchy
from xivo.http_helpers import DEFAULT_CIPHERS
from xivo.xivo_logging import get_log_level_by_name

_DEFAULT_CONFIG = {
    'auth': {
        'host': 'localhost',
        'port': 9497
    },
    'config_file': '/etc/xivo-dird/config.yml',
    'consul': {
        'scheme': 'https',
        'host': 'localhost',
        'port': 8500,
        'verify': '/usr/share/xivo-certs/server.crt',
    },
    'extra_config_files': '/etc/xivo-dird/conf.d/',
    'debug': False,
    'enabled_plugins': {
        'backends': [],
        'services': [],
        'views': [],
    },
    'log_level': 'info',
    'log_filename': '/var/log/xivo-dird.log',
    'foreground': False,
    'pid_filename': '/var/run/xivo-dird/xivo-dird.pid',
    'rest_api': {
        'https': {
            'listen': '0.0.0.0',
            'port': 9489,
            'certificate': '/usr/share/xivo-certs/server.crt',
            'private_key': '/usr/share/xivo-certs/server.key',
            'ciphers': DEFAULT_CIPHERS,
        },
        'cors': {
            'enabled': True,
            'allow_headers': 'Content-Type, X-Auth-Token'
        },
    },
    'services': {},
    'source_config_dir': '/etc/xivo-dird/sources.d',
    'user': 'www-data',
    'views': {},
    'sources': {},
}


def load(logger, argv):
    cli_config = _parse_cli_args(argv)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    _validate_configuration(file_config, logger)
    reinterpreted_config = _get_reinterpreted_raw_values(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    source_dir_configuration = _load_source_config_dir(logger, ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    return ChainMap(reinterpreted_config, source_dir_configuration, cli_config, file_config, _DEFAULT_CONFIG)


def _load_source_config_dir(logger, config):
    source_config_dir = config.get('source_config_dir')
    if not source_config_dir:
        return {}

    source_configs = parse_config_dir(source_config_dir)
    sources = {}
    for source_config in source_configs:
        source_name = source_config.get('name')
        if not source_name:
            logger.warning('One of the configs has no name. Ignoring.')
            logger.debug('Source config with no name: `%s`', config)
            continue

        sources[source_name] = source_config

    return {'sources': sources}


def _parse_cli_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--config-file',
                        action='store',
                        help="The path where is the config file. Default: %(default)s")
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="Log debug messages. Overrides log_level. Default: %(default)s")
    parser.add_argument('-f',
                        '--foreground',
                        action='store_true',
                        help="Foreground, don't daemonize. Default: %(default)s")
    parser.add_argument('-l',
                        '--log-level',
                        action='store',
                        help="Logs messages with LOG_LEVEL details. Must be one of:\n"
                             "critical, error, warning, info, debug. Default: %(default)s")
    parser.add_argument('-u',
                        '--user',
                        action='store',
                        help="The owner of the process.")
    parsed_args = parser.parse_args(argv)

    result = {}
    if parsed_args.config_file:
        result['config_file'] = parsed_args.config_file
    if parsed_args.debug:
        result['debug'] = parsed_args.debug
    if parsed_args.foreground:
        result['foreground'] = parsed_args.foreground
    if parsed_args.log_level:
        result['log_level'] = parsed_args.log_level
    if parsed_args.user:
        result['user'] = parsed_args.user

    return result


def _get_reinterpreted_raw_values(config):
    result = {}

    log_level = config.get('log_level')
    if log_level:
        result['log_level'] = get_log_level_by_name(log_level)

    return result


def _validate_configuration(config, logger):
    _validate_views_displays(config.get('views', {}).get('displays', {}), logger)


def _validate_views_displays(displays, logger):
    for profile, values in displays.iteritems():
        if _multiple_profile_type_number(values):
            logger.warning('%s: Only one type: \'number\' is supported per profile', profile)


def _multiple_profile_type_number(profile):
    cpt = 0
    for values in profile:
        cpt += 1 if values.get('type') == 'number' else 0
    return True if cpt > 1 else False
