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

import logging

from stevedore.named import NamedExtensionManager

from xivo_dird.core.source_manager import SourceManager

logger = logging.getLogger(__name__)
services_extension_manager = None


def load_services(config, enabled_services, sources):
    global services_extension_manager
    services_extension_manager = NamedExtensionManager(
        namespace='xivo_dird.services',
        names=enabled_services,
        name_order=True,
        invoke_on_load=True)

    return dict(services_extension_manager.map(load_service_extension, config, sources))


def load_service_extension(extension, config, sources):
    logger.debug('loading extension %s...', extension.name)
    args = {
        'config': config,
        'sources': sources,
    }
    return extension.name, extension.obj.load(args)


def unload_services():
    services_extension_manager.map_method('unload')


def load_sources(enabled_backends, source_configs):
    return SourceManager(enabled_backends, source_configs).load_sources()


def load_views(config, enabled_views, services, rest_api):
    extension_manager = NamedExtensionManager(
        namespace='xivo_dird.views',
        names=enabled_views,
        name_order=True,
        invoke_on_load=True)

    extension_manager.map(load_view_extension, config, services, rest_api)


def load_view_extension(extension, config, services, rest_api):
    logger.debug('loading extension %s...', extension.name)
    args = {
        'config': config,
        'http_app': rest_api.app,
        'rest_api': rest_api.api,
        'services': services,
    }
    extension.obj.load(args)
