# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
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
DIRD_TOKEN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee1'
VALID_TOKEN_MAIN_TENANT = 'valid-token-master-tenant'
MAIN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10'
MAIN_USER_UUID = '5f243438-a429-46a8-a992-baed872081e0'
SUB_TENANT = '00000000-0000-4000-8000-000000000202'
USER_1_UUID = '00000000-0000-4000-8000-000000000302'
VALID_TOKEN_SUB_TENANT = '00000000-0000-4000-8000-000000000102'
USER_2_UUID = '00000000-0000-4000-8000-000000000303'
USER_2_TOKEN = '00000000-0000-4000-8000-000000000103'
WAZO_UUID = '00000000-0000-4000-8000-00003eb8004d'
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
UNKNOWN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee11'
UNKNOWN_UUID = '00000000-0000-0000-0000-000000000000'

HTTP_400 = has_properties(response=has_properties(status_code=400))
HTTP_401 = has_properties(response=has_properties(status_code=401))
HTTP_404 = has_properties(response=has_properties(status_code=404))
HTTP_409 = has_properties(response=has_properties(status_code=409))
