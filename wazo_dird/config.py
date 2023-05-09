# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse

from xivo.chain_map import ChainMap
from xivo.config_helper import parse_config_file, read_config_file_hierarchy
from xivo.xivo_logging import get_log_level_by_name

_DEFAULT_HTTPS_PORT = 9489
_DEFAULT_CONFIG = {
    'auth': {
        'host': 'localhost',
        'port': 9497,
        'prefix': None,
        'https': False,
        'key_file': '',
    },
    'config_file': '/etc/wazo-dird/config.yml',
    'db_uri': 'postgresql://asterisk:proformatique@localhost/asterisk',
    'debug': False,
    'extra_config_files': '/etc/wazo-dird/conf.d/',
    'enabled_plugins': {
        'backends': {
            'conference': True,
            'csv': True,
            'csv_ws': True,
            'google': True,
            'ldap': True,
            'office365': True,
            'personal': True,
            'phonebook': True,
            'wazo': True,
        },
        'services': {
            'cleanup': True,
            'config': True,
            'display': True,
            'favorites': True,
            'lookup': True,
            'personal': True,
            'phonebook': True,
            'profile': True,
            'reverse': True,
            'source': True,
        },
        'views': {
            'api_view': True,
            'backends_view': True,
            'conference_view': True,
            'config_view': True,
            'csv_backend': True,
            'csv_ws_backend': True,
            'default_json': True,
            'displays_view': True,
            'google_view': True,
            'graphql_view': True,
            'headers_view': True,
            'ldap_backend': True,
            'office365_backend': True,
            'personal_backend': True,
            'personal_view': True,
            'phonebook_backend': True,
            'phonebook_view': True,
            'profile_sources_view': True,
            'profiles_view': True,
            'sources_view': True,
            'status_view': True,
            'wazo_backend': True,
        },
    },
    'log_level': 'info',
    'log_filename': '/var/log/wazo-dird.log',
    'rest_api': {
        'listen': '127.0.0.1',
        'port': _DEFAULT_HTTPS_PORT,
        'certificate': None,  # Deprecated
        'private_key': None,  # Deprecated
        'cors': {
            'enabled': True,
            'allow_headers': ['Content-Type', 'X-Auth-Token', 'Wazo-Tenant'],
        },
        'max_threads': 10,
    },
    'services': {
        'service_discovery': {
            'template_path': '/etc/wazo-dird/templates.d/',
            'services': {},
        }
    },
    'user': 'www-data',
    'bus': {
        'enabled': True,
        'username': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': 5672,
        'exchange_name': 'wazo-headers',
        'exchange_type': 'headers',
    },
    'consul': {
        'scheme': 'http',
        'port': 8500,
    },
    'service_discovery': {
        'enabled': False,
        'advertise_address': 'auto',
        'advertise_port': _DEFAULT_HTTPS_PORT,
        'advertise_address_interface': 'eth0',
        'refresh_interval': 27,
        'retry_interval': 2,
        'ttl_interval': 30,
        'extra_tags': [],
    },
}


def load(argv):
    cli_config = _parse_cli_args(argv)
    file_config = read_config_file_hierarchy(ChainMap(cli_config, _DEFAULT_CONFIG))
    reinterpreted_config = _get_reinterpreted_raw_values(
        ChainMap(cli_config, file_config, _DEFAULT_CONFIG)
    )
    key_file = _load_key_file(ChainMap(cli_config, file_config, _DEFAULT_CONFIG))

    return ChainMap(
        reinterpreted_config, key_file, cli_config, file_config, _DEFAULT_CONFIG
    )


def _parse_cli_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--config-file',
        action='store',
        help="The path where is the config file. Default: %(default)s",
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        help="Log debug messages. Overrides log_level. Default: %(default)s",
    )
    parser.add_argument(
        '-l',
        '--log-level',
        action='store',
        help="Logs messages with LOG_LEVEL details. Must be one of:\n"
        "critical, error, warning, info, debug. Default: %(default)s",
    )
    parser.add_argument(
        '-u', '--user', action='store', help="The owner of the process."
    )
    parsed_args = parser.parse_args(argv)

    result = {}
    if parsed_args.config_file:
        result['config_file'] = parsed_args.config_file
    if parsed_args.debug:
        result['debug'] = parsed_args.debug
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

    return {
        'auth': {
            'username': key_file['service_id'],
            'password': key_file['service_key'],
        }
    }


def _get_reinterpreted_raw_values(config):
    result = {}

    log_level = config.get('log_level')
    if log_level:
        result['log_level'] = get_log_level_by_name(log_level)

    return result
