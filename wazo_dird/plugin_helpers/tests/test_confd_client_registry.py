# Copyright 2019-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from mock import Mock, patch
from copy import deepcopy

from ..confd_client_registry import _Registry


SOURCE_CONFIG = {
    'uuid': '9d3f8211-1217-4461-9d0e-ce5e6ddedf2f',
    'tenant_uuid': 'f5a28c60-acb7-4dcb-9108-0a68c426f9ce',
    'auth': {
        'key_file': 'key.yml',
    },
    'confd': {},
}


@patch('wazo_dird.plugin_helpers.confd_client_registry.AuthClient', Mock())
@patch('wazo_dird.plugin_helpers.confd_client_registry.TokenRenewer', Mock())
@patch(
    'wazo_dird.plugin_helpers.confd_client_registry.parse_config_file',
    Mock(return_value={'service_id': 'serv_id', 'service_key': 'serv_key'}),
)
class TestClientRegistry(TestCase):
    def setUp(self):
        self.registry = _Registry()
        self.confd_client = (
            patch('wazo_dird.plugin_helpers.confd_client_registry.ConfdClient')
            .start()
            .return_value
        )

    def tearDown(self):
        self.registry.unregister_all()

    def test_set_tenant_with_key_file(self):
        self.registry.get(SOURCE_CONFIG)
        assert self.confd_client.tenant_uuid == SOURCE_CONFIG['tenant_uuid']

    def test_set_tenant_without_key_file(self):
        config = deepcopy(SOURCE_CONFIG)
        del config['auth']['key_file']
        self.registry.get(config)
        assert self.confd_client.tenant_uuid != SOURCE_CONFIG['tenant_uuid']
