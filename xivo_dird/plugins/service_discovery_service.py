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
import threading
import time
from uuid import UUID

import kombu
import requests
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.services.event import ServiceRegisteredEvent
from xivo_dird import BaseServicePlugin
from xivo_dird.core.plugin_manager import source_manager

logger = logging.getLogger(__name__)


class ServiceDiscoveryServicePlugin(BaseServicePlugin):

    def __init__(self):
        self._service = None

    def load(self, args):
        config = args['config']
        bus = args['bus']

        self._service = _Service(config, bus)


class _Service(object):

    QUEUE = kombu.Queue(exchange=kombu.Exchange('xivo', type='topic'),
                        routing_key='service.registered.*',
                        exclusive=True)

    def __init__(self, config, bus):
        self._config = config
        service_disco_config = config['services'].get('service_discovery')
        if not service_disco_config:
            logger.info('"service_discovery" key missing from the configuration')
            return
        self._source_config_generator = SourceConfigGenerator(service_disco_config)
        self._source_config_manager = SourceConfigManager(config['sources'])
        self._profile_config_updater = ProfileConfigUpdater(config)
        bus.add_consumer(self.QUEUE, self._on_service_registered)
        fetcher = RemoteServiceFetcher(config['consul'])

        fetcher_thread = threading.Thread(target=self._add_remote_services,
                                          args=(fetcher, service_disco_config))
        fetcher_thread.daemon = True
        fetcher_thread.start()

    def _add_remote_services(self, fetcher, service_disco_config):
        logger.info('Fetcher starting')
        while True:
            try:
                for service_name in service_disco_config['services']:
                    for uuid, host, port in fetcher.fetch(service_name):
                        logger.info('%s %s %s %s', service_name, uuid, host, port)
                        self._on_service_added(service_name, host, port, uuid)
                logger.debug('Fetcher done')
                return
            except Exception:
                logger.info('failed to find running services')
                time.sleep(2)

    def _on_service_added(self, service_name, host, port, uuid):
        logger.debug('%s registered %s:%s with uuid %s', service_name, host, port, uuid)
        config = self._source_config_generator.generate_from_new_service(
            service_name, uuid, host, port)
        if not config:
            return

        source_name = config.get('name')
        if self._source_config_manager.source_exists(source_name):
            return

        self._source_config_manager.add_source(config)
        source_manager.load_source(config['type'], source_name)
        self._profile_config_updater.on_service_added(source_name, service_name)
        logger.info('new source added %s', source_name)

    def _on_service_registered(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, ServiceRegisteredEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            uuid = _find_first_uuid(event.tags)
            if uuid:
                self._on_service_added(event.service_name,
                                       event.advertise_address,
                                       event.advertise_port,
                                       uuid)
            message.ack()


def _find_first_uuid(tags):
    for tag in tags:
        try:
            return str(UUID(tag))
        except (AttributeError, ValueError):
            continue


class RemoteServiceFetcher(object):

    def __init__(self, consul_config):
        self._url = '{scheme}://{host}:{port}/v1'.format(**consul_config)
        self._verify = consul_config['verify']

    def fetch(self, service_name):
        for datacenter in self._datacenters():
            checks = self._checks(service_name, datacenter)
            for service in self._service(service_name, datacenter):
                if service['ServiceID'] not in checks:
                    continue
                yield (_find_first_uuid(service['ServiceTags']),
                       service['ServiceAddress'],
                       service['ServicePort'])

    def _checks(self, service_name, datacenter):
        response = requests.get('{}/health/checks/{}'.format(self._url, service_name),
                                verify=self._verify,
                                params={'db': datacenter})
        return set([service['ServiceID']
                    for service in response.json()
                    if service['Status'] == 'passing'])

    def _datacenters(self):
        response = requests.get('{}/catalog/datacenters'.format(self._url),
                                verify=self._verify)
        for datacenter in response.json():
            yield datacenter

    def _service(self, service_name, datacenter):
        response = requests.get('{}/catalog/service/{}'.format(self._url, service_name),
                                verify=self._verify,
                                params={'dc': datacenter})
        for service in response.json():
            yield service


class SourceConfigManager(object):

    def __init__(self, config):
        self._config = config

    def source_exists(self, source_name):
        return source_name in self._config

    def add_source(self, source_config):
        source_name = source_config.get('name')
        if not source_name:
            return
        self._config[source_name] = source_config


class ProfileConfigUpdater(object):

    def __init__(self, config):
        self._config = config
        self._watched_services = {}
        self._host_configs = config['services']['service_discovery']['hosts']
        consul_services = config['services']['service_discovery']['services']
        for name, config in consul_services.iteritems():
            self._watched_services[name] = {
                'lookup': self._profiles_for(config, 'lookup'),
                'reverse': self._profiles_for(config, 'reverse'),
                'favorites': self._profiles_for(config, 'favorites'),
            }

    def on_service_added(self, source_name, discovered_service):
        consul_service_config = self._watched_services.get(discovered_service)
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
        logger.debug('Starting with %s', service_discovery_config)
        template_path = service_discovery_config.get('template_path')
        if not template_path:
            logger.info('service discovery service error: no "template_path" configured')
            return

        loader = FileSystemLoader(template_path)
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
            logger.info('no template configured for service %s', service)
            return

        try:
            template = self._env.get_template(template_file)
        except TemplateNotFound:
            logger.info('template found with name %s', template_file)
            return

        template_args = dict(self._host_configs[uuid])
        template_args['uuid'] = uuid
        template_args['hostname'] = host
        template_args['port'] = port

        yaml_representation = template.render(template_args)
        return yaml.load(yaml_representation)
