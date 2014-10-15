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

from stevedore import enabled


def load_services(config, rest_api):
    check_func = functools.partial(services_filter, config)
    manager = enabled.EnabledExtensionManager(
        namespace='xivo-dird.services',
        check_func=check_func,
        invoke_on_load=True)

    manager.map(load_service_extension, config, rest_api)


def load_service_extension(extension, config, rest_api):
    args = {
        'http_app': rest_api.app,
        'http_namespace': rest_api.namespace,
        'http_api': rest_api.api,
        'config': config.get(extension.name, {})
    }
    extension.load(args)


def services_filter(config, extension):
    return config.get(extension.name, {}).get('enabled', False)
