# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.config_helper import parse_config_file
from xivo_auth_client import Client as AuthClient
from xivo_confd_client import Client as ConfdClient

from wazo_dird import exception


class ContactLister:

    def __init__(self, client):
        self._client = client

    def list(self, *args, **kwargs):
        try:
            return self._client.users.list(*args, view='directory', **kwargs)
        except Exception as e:
            raise exception.XiVOConfdError(self._client, e)

    @classmethod
    def from_config(cls, source_config):
        auth_config = source_config['auth']
        if auth_config.get('key_file'):
            # File must be readable by wazo-dird
            key_file = parse_config_file(auth_config.pop('key_file'))
            auth_config['username'] = key_file['service_id']
            auth_config['password'] = key_file['service_key']
        auth = AuthClient(**source_config['auth'])
        token = auth.token.new(backend='wazo_user', expiration='60')['token']
        confd = ConfdClient(token=token, **source_config['confd'])
        confd.set_tenant(source_config['tenant_uuid'])
        return cls(confd)
