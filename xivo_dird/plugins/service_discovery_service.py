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

import logging

from uuid import UUID

import kombu
import yaml

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.services.event import ServiceRegisteredEvent

from xivo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)


class ServiceDiscoveryServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        config = args['config']
        bus = args['bus']

        self._service = _Service(config, bus)


class _Service(object):

    def __init__(self, config, bus):
        self._config = config
        queue = kombu.Queue(exchange=kombu.Exchange('xivo', type='topic'),
                            routing_key='service.registered.*',
                            exclusive=True)
        bus.add_consumer(queue, self._on_service_registered)

    def _on_service_added(self, service_name, host, port, uuid):
        logger.info('%s registered %s:%s with uuid %s', service_name, host, port, uuid)

    def _on_service_registered(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, ServiceRegisteredEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            uuid = self._find_first_uuid(event.tags)
            if uuid:
                self._on_service_added(event.service_name,
                                       event.advertise_address,
                                       event.advertise_port,
                                       uuid)
            message.ack()

    @staticmethod
    def _find_first_uuid(tags):
        for tag in tags:
            try:
                return str(UUID(tag))
            except (AttributeError, ValueError):
                continue


class ProfileConfigUpdater(object):

    def __init__(self, config):
        self._config = config
        self._watched_services = {}
        self._host_configs = config['services']['service_discovery']['hosts']
        consul_services = config['services']['service_discovery']['services']
        for name, config in consul_services.iteritems():
            self._watched_services[name] = {
                'template': config['template'],
                'lookup': self._profiles_for(config, 'lookup'),
                'reverse': self._profiles_for(config, 'reverse'),
                'favorites': self._profiles_for(config, 'favorites'),
            }

    def on_service_added(self, source_name, new_service_msg):
        consul_service = new_service_msg.get('service')
        consul_service_config = self._watched_services.get(consul_service)
        if not consul_service_config:
            return

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

    @staticmethod
    def _profiles_for(config, service):
        profiles = config.get(service, {})
        return [profile for profile, enabled in profiles.iteritems() if enabled]


class SourceConfigGenerator(object):

    enabled = False

    def __init__(self, service_discovery_config):
        template_path = service_discovery_config['template_path']
        if not template_path:
            logger.info('service discovery service error: no "template_path" configured')
            return

        loader = FileSystemLoader(service_discovery_config['template_path'])
        self._env = Environment(loader=loader)
        self._host_configs = service_discovery_config['hosts']
        self._template_files = {
            service: config['template']
            for service, config
            in service_discovery_config['services'].iteritems()
        }
        self.enabled = True

    def generate_from_new_service(self, service, uuid, host, port):
        if not self.enabled:
            return

        template_file = self._template_files.get(service)
        if not template_file:
            return

        try:
            template = self._env.get_template(template_file)
        except TemplateNotFound:
            return

        template_args = dict(self._host_configs[uuid])
        template_args['uuid'] = uuid
        template_args['hostname'] = host
        template_args['port'] = port

        yaml_representation = template.render(template_args)
        return yaml.load(yaml_representation)
