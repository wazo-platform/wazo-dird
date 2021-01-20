# Copyright 2016-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import threading
import time
from uuid import UUID

import kombu
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from xivo.consul_helpers import ServiceFinder
from xivo_bus.marshaler import InvalidMessage, Marshaler
from xivo_bus.resources.services.event import ServiceRegisteredEvent
from wazo_dird import BaseServicePlugin

logger = logging.getLogger(__name__)


class ServiceDiscoveryServicePlugin(BaseServicePlugin):
    def __init__(self):
        self._service = None

    def load(self, dependencies):
        config = dependencies['config']
        bus = dependencies['bus']
        source_manager = dependencies['source_manager']
        controller = dependencies['controller']

        self._service = _Service(config, bus, source_manager, controller)


class _Service:

    QUEUE = kombu.Queue(
        exchange=kombu.Exchange('xivo', type='topic'),
        routing_key='service.registered.*',
        exclusive=True,
    )

    def __init__(self, config, bus, source_manager, controller):
        self._controller = controller
        self._config = config
        self._source_manager = source_manager
        service_disco_config = config['services'].get('service_discovery')
        if not service_disco_config:
            logger.info('"service_discovery" key missing from the configuration')
            return
        self._source_config_generator = SourceConfigGenerator(service_disco_config)
        self._profile_config_updater = ProfileConfigUpdater(config)
        bus.add_consumer(self.QUEUE, self._on_service_registered)
        finder = ServiceFinder(config['consul'])

        fetcher_thread = threading.Thread(
            target=self._add_remote_services, args=(finder, service_disco_config)
        )
        fetcher_thread.daemon = True
        fetcher_thread.start()

    def _add_remote_services(self, finder, service_disco_config):
        logger.info('Searching for remote services...')
        while True:
            try:
                for service_name in service_disco_config['services']:
                    for service in finder.list_healthy_services(service_name):
                        uuid = _find_first_uuid(service['Tags'])
                        if not uuid:
                            continue
                        host = service['Address']
                        port = service['Port']
                        self._on_service_added(service_name, host, port, uuid)
                logger.debug('Searching done')
                return
            except Exception as e:
                logger.info('failed to find running services: %s', e)
                time.sleep(2)

    def _on_service_added(self, service_name, host, port, uuid):
        logger.debug('%s registered %s:%s with uuid %s', service_name, host, port, uuid)
        config = self._source_config_generator.generate_from_new_service(
            service_name, uuid, host, port
        )
        if not config:
            return

        source_name = config.get('name')
        source_service = self._controller.services['source']
        if self._source_exists(source_service, config):
            return

        source_service.create('wazo', **config)
        self._profile_config_updater.on_service_added(source_name, service_name)
        logger.info('new source added %s', source_name)

    def _source_exists(self, source_service, config):
        search_params = {
            'backend': 'wazo',
            'visible_tenants': [config['tenant_uuid']],
            'name': config['name'],
        }
        return True if source_service.list_(**search_params) else False

    def _on_service_registered(self, body, message):
        try:
            event = Marshaler.unmarshal_message(body, ServiceRegisteredEvent)
        except (InvalidMessage, KeyError):
            logger.exception('Ignoring the following malformed bus message: %s', body)
        else:
            uuid = _find_first_uuid(event.tags)
            if uuid:
                self._on_service_added(
                    event.service_name,
                    event.advertise_address,
                    event.advertise_port,
                    uuid,
                )


def _find_first_uuid(tags):
    for tag in tags:
        try:
            return str(UUID(tag))
        except (AttributeError, ValueError):
            continue


class ProfileConfigUpdater:
    def __init__(self, config):
        self._config = config
        self._watched_services = {}
        self._host_configs = config['services']['service_discovery']['hosts']
        consul_services = config['services']['service_discovery']['services']
        for name, config in consul_services.items():
            self._watched_services[name] = {
                'lookup': self._profiles_for(config, 'lookup'),
                'reverse': self._profiles_for(config, 'reverse'),
                'favorites': self._profiles_for(config, 'favorites'),
            }

    def on_service_added(self, source_name, discovered_service):
        consul_service_config = self._watched_services.get(discovered_service)
        if not consul_service_config:
            return

        for dird_service, profiles in consul_service_config.items():
            dird_service_config = self._config['services'].get(dird_service)
            if not dird_service_config:
                continue

            for profile in profiles:
                if profile not in dird_service_config:
                    dird_service_config[profile] = {'sources': {}}
                if 'sources' not in dird_service_config[profile]:
                    dird_service_config[profile]['sources'] = {}

                dird_service_config[profile]['sources'][source_name] = True

    @staticmethod
    def _profiles_for(config, service):
        profiles = config.get(service, {})
        return [profile for profile, enabled in profiles.items() if enabled]


class SourceConfigGenerator:

    enabled = False

    def __init__(self, service_discovery_config):
        logger.debug('Starting with %s', service_discovery_config)
        template_path = service_discovery_config.get('template_path')
        if not template_path:
            logger.info(
                'service discovery service error: no "template_path" configured'
            )
            return

        loader = FileSystemLoader(template_path)
        self._env = Environment(loader=loader)
        self._host_configs = service_discovery_config['hosts']
        self._template_files = {
            service: config['template']
            for service, config in service_discovery_config['services'].items()
        }
        self.enabled = True

    def generate_from_new_service(self, service, uuid, host, port):
        if not self.enabled:
            return

        if uuid not in self._host_configs:
            return

        template_file = self._template_files.get(service)
        if not template_file:
            logger.info('no template configured for service %s', service)
            return

        try:
            template = self._env.get_template(template_file)
        except TemplateNotFound:
            logger.info('no template found with name %s', template_file)
            return

        template_args = dict(self._host_configs[uuid])
        template_args['uuid'] = uuid
        template_args['hostname'] = host
        template_args['port'] = port

        yaml_representation = template.render(template_args)
        return yaml.safe_load(yaml_representation)
