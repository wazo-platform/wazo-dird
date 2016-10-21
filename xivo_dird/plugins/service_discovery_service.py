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

import yaml

from jinja2 import Environment, FileSystemLoader

from xivo_dird import BaseServicePlugin


class ServiceDiscoveryServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        pass


class _Service(object):

    def __init__(self):
        pass


class ConfigUpdater(object):

    def __init__(self, config):
        self._config = config
        self._watched_services = {}
        services = config['services']['service_discovery']['services']
        self._host_configs = config['services']['service_discovery']['hosts']
        template_path = config['services']['service_discovery']['template_path']
        loader = FileSystemLoader(template_path)
        self.env = Environment(loader=loader)
        for name, config in services.iteritems():
            self._watched_services[name] = {
                'lookup': self._profiles_for(config, 'lookup'),
                'reverse': self._profiles_for(config, 'reverse'),
                'favorites': self._profiles_for(config, 'favorites'),
            }

    def on_service_added(self, new_service_msg):
        consul_service = new_service_msg.get('service')
        consul_service_config = self._watched_services.get(consul_service)
        if not consul_service_config:
            return

        host_config = self._host_configs.get(new_service_msg.get('uuid'))
        if not host_config:
            return

        source_config = self.build_source_config(
            consul_service_config.get('template'),
            new_service_msg,
            host_config)

        source_name = source_config['name']
        for dird_service, profiles in consul_service_config.iteritems():
            dird_service_config = self._config['services'].get(dird_service)
            if not dird_service_config:
                continue

            for profile in profiles:
                if profile not in dird_service_config:
                    dird_service_config[profile] = {'sources': []}
                sources = dird_service_config[profile].get('sources') or []
                if source_name not in sources:
                    sources.append(source_name)
                    dird_service_config[profile]['sources'] = sources

    def build_source_config(self, template_filename, new_service_msg, host_config):
        template_args = {}
        for d in [new_service_msg, host_config]:
            for k, v in d.iteritems():
                template_args[k] = v

        template = self.env.get_template(template_filename)
        yaml_representation = template.render(template_args)
        return yaml.load(yaml_representation)

    @staticmethod
    def _profiles_for(config, service):
        profiles = config.get(service, {})
        return [profile for profile, enabled in profiles.iteritems() if enabled]
