# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from collections import namedtuple
from threading import Lock

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo.config_helper import parse_config_file
from xivo.token_renewer import TokenRenewer

logger = logging.getLogger(__name__)

RegisteredClient = namedtuple('RegisteredClient', ['client', 'token_renewer'])


class _Registry:
    def __init__(self):
        self._clients = {}
        self._clients_lock = Lock()

    def get(self, source_config):
        source_uuid = source_config['uuid']

        with self._clients_lock:
            if source_uuid not in self._clients:
                self._add_client(source_config)

            return self._clients[source_uuid].client

    def unregister_all(self):
        with self._clients_lock:
            for _, renewer in self._clients.values():
                renewer.stop()
            self._clients = {}

    def _add_client(self, source_config):
        logger.debug('Instanciating a new confd client for %s', source_config['uuid'])
        auth_config = dict(source_config['auth'])
        if auth_config.get('key_file'):
            # File must be readable by wazo-dird
            key_file = parse_config_file(auth_config.pop('key_file'))
            if not key_file:
                logger.info(
                    'failed to load key file for source %s', source_config['name']
                )
                return
            auth_config['username'] = key_file['service_id']
            auth_config['password'] = key_file['service_key']
        auth_client = AuthClient(**auth_config)
        token_renewer = TokenRenewer(auth_client)

        confd_config = source_config['confd']
        logger.debug('confd config %s', confd_config)
        client = ConfdClient(**confd_config)
        client.set_tenant(source_config['tenant_uuid'])

        token_renewer.subscribe_to_token_change(client.set_token)
        token_renewer.start()

        self._clients[source_config['uuid']] = RegisteredClient(client, token_renewer)


registry = _Registry()
