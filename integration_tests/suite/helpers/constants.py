# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid
import os

ASSET_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
CA_CERT = os.path.join(ASSET_ROOT, 'ssl', 'dird', 'server.crt')
DB_URI_FMT = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}/asterisk')
VALID_UUID = 'uuid-tenant-master'
VALID_UUID_1 = 'uuid-1'
VALID_TOKEN_1 = 'valid-token-1'
VALID_TOKEN_2 = 'valid-token-2'
VALID_TOKEN_NO_ACL = 'valid-token-no-acl'
VALID_TOKEN_MAIN_TENANT = 'valid-token-master-tenant'
MAIN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10'
DIRD_TOKEN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1'
DEFAULT_DISPLAYS = [
    {
        'name': 'default_display',
        'columns': [
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'number'},
        ],
    },
]
TENANT_UUID_2 = str(uuid.uuid4())
