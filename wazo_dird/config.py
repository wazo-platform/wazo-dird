# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import argparse

from xivo.chain_map import ChainMap
from xivo.config_helper import (
    parse_config_dir,
    parse_config_file,
    read_config_file_hierarchy,
)
from xivo.xivo_logging import get_log_level_by_name

_DEFAULT_HTTPS_PORT = 9489
_DEFAULT_CONFIG = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'verify_certificate': '/usr/share/xivo-certs/server.crt',
        'key_file': '',
    },
    'config_file': '/etc/wazo-dird/config.yml',
    'consul': {
        'scheme': 'https',
        'host': 'localhost',
        'port': 8500,
        'verify': '/usr/share/xivo-certs/server.crt',
    },
    'extra_config_files': '/etc/wazo-dird/conf.d/',
    'debug': False,
    'enabled_plugins': {
        'backends': {},
        'services': {},
        'views': {},
    },
    'log_level': 'info',
    'log_filename': '/var/log/wazo-dird.log',
    'foreground': False,
    'pid_filename': '/var/run/wazo-dird/wazo-dird.pid',
    'rest_api': {
        'https': {
            'listen': '0.0.0.0',
            'port': _DEFAULT_HTTPS_PORT,
            'certificate': '/usr/share/xivo-certs/server.crt',
            'private_key': '/usr/share/xivo-certs/server.key',
        },
        'cors': {
            'enabled': True,
            'allow_headers': ['Content-Type', 'X-Auth-Token'],
        },
    },
    'services': {
        'service_discovery': {
            'template_path': '/etc/wazo-dird/templates.d/',
            'services': {},
        },
    },
    'source_config_dir': '/etc/wazo-dird/sources.d',
    'user': 'www-data',
    'views': {},
    'sources': {},
    'bus': {
        'enabled': True,
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': 5672,
        'exchange_name': 'xivo',
        'exchange_type': 'topic',
        'exchange_durable': True,
    },
    'service_discovery': {
        'enabled': True,
        'advertise_address': 'localhost',
        'advertise_port': _DEFAULT_HTTPS_PORT,
        'advertise_address_interface': 'eth0',
        'refresh_interval': 25,
        'retry_interval': 2,
        'ttl_interval': 30,
        'extra_tags': [],
    },
}


def load(logger, argv):
    cli_config = _parse_cli_args(argv)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    _validate_configuration(file_config, logger)
    reinterpreted_config = _get_reinterpreted_raw_values(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    source_dir_configuration = _load_source_config_dir(logger, ChainMap(cli_config, file_config, _DEFAULT_CONFIG))
    key_file = _load_key_file(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))

    return ChainMap(
        reinterpreted_config,
        key_file,
        source_dir_configuration,
        cli_config,
        file_config,
        _DEFAULT_CONFIG,
    )


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


def _load_key_file(config):
    filename = config.get('auth', {}).get('key_file')
    if not filename:
        return {}

    key_file = parse_config_file(filename)
    if not key_file:
        return {}

    return {'auth': {'username': key_file['service_id'], 'password': key_file['service_key']}}


def _get_reinterpreted_raw_values(config):
    result = {}

    log_level = config.get('log_level')
    if log_level:
        result['log_level'] = get_log_level_by_name(log_level)

    return result


def _validate_configuration(config, logger):
    _validate_views_displays(config.get('views', {}).get('displays', {}), logger)


def _validate_views_displays(displays, logger):
    for profile, values in displays.items():
        if _multiple_profile_type_number(values):
            logger.warning('%s: Only one type: \'number\' is supported per profile', profile)


def _multiple_profile_type_number(profile):
    column_types = [values.get('type') for values in profile]
    return column_types.count('number') > 1
