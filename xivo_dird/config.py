# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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

from __future__ import print_function

import argparse
import sys
import yaml


def load(argv):
    default_config = {
        'config_file': '/etc/xivo/xivo-dird/xivo-dird.yml',
        'debug': False,
        'log_filename': '/var/log/xivo-dird.log',
        'foreground': False,
        'pid_filename': '/var/run/xivo-dird/xivo-dird.pid',
        'rest_api': {
            'wsgi_socket': '/var/run/xivo-dird/xivo-dird.sock',
        },
        'services': {},
        'user': 'www-data',
    }
    config = dict(default_config)

    config.update(_parse_cli_args(argv, default_config))
    try:
        with open(config['config_file']) as config_file:
            config.update(yaml.load(config_file))
    except IOError as e:
        print('Could not read config file {}: {}'.format(config['config_file'], e), file=sys.stderr)

    return config


def _parse_cli_args(argv, default_config):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--config-file',
                        action='store',
                        default=default_config['config_file'],
                        help="The path where is the config file. Default: %(default)s")
    parser.add_argument('-f',
                        '--foreground',
                        action='store_true',
                        default=default_config['foreground'],
                        help="Foreground, don't daemonize. Default: %(default)s")
    parser.add_argument('-u',
                        '--user',
                        action='store',
                        default=default_config['user'],
                        help="The owner of the process.")
    parsed_args = parser.parse_args(argv)
    return vars(parsed_args)
