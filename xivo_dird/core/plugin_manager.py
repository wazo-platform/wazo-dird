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

import functools
import logging

from stevedore import enabled

logger = logging.getLogger(__name__)
extension_manager = None


def load_services(config, rest_api):
    global extension_manager
    check_func = functools.partial(services_filter, config)
    extension_manager = enabled.EnabledExtensionManager(
        namespace='xivo_dird.services',
        check_func=check_func,
        invoke_on_load=True)

    extension_manager.map(load_service_extension, config, rest_api)


def load_service_extension(extension, config, rest_api):
    logger.info('loading extension {}...'.format(extension.name))
    args = {
        'config': config.get(extension.name, {})
    }
    extension.obj.load(args)


def services_filter(config, extension):
    return config.get(extension.name, {}).get('enabled', False)


def unload_services():
    extension_manager.map_method('unload')
