# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from hamcrest import has_properties

ASSET_ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
DB_URI_FMT = os.getenv(
    'DB_URI', 'postgresql://wazo-dird:Secr7t@127.0.0.1:{port}/wazo-dird'
)
VALID_UUID = 'uuid-tenant-master'
VALID_UUID_1 = 'uuid-1'
VALID_TOKEN = 'valid-token'
VALID_TOKEN_1 = 'valid-token-1'
VALID_TOKEN_2 = 'valid-token-2'
VALID_TOKEN_NO_ACL = 'valid-token-no-acl'
VALID_TOKEN_MAIN_TENANT = 'valid-token-master-tenant'
VALID_TOKEN_SUB_TENANT = 'valid-token-sub-tenant'
MAIN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10'
DIRD_TOKEN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1'
SUB_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee11'
DEFAULT_DISPLAYS = [
    {
        'name': 'default_display',
        'columns': [
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'number'},
        ],
    }
]
TENANT_UUID_2 = '4c3c6c6f-7dda-4561-9cc0-a2d757c725dd'
UNKNOWN_UUID = '00000000-0000-0000-0000-000000000000'

HTTP_400 = has_properties(response=has_properties(status_code=400))
HTTP_401 = has_properties(response=has_properties(status_code=401))
HTTP_404 = has_properties(response=has_properties(status_code=404))
HTTP_409 = has_properties(response=has_properties(status_code=409))
