# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource


class Sources(AuthResource):

    @required_acl('dird.backends.wazo.sources.create')
    def post(self):
        return {'uuid': 'foobar'}, 201
