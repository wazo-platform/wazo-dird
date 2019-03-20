# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource


class _BaseResource(AuthResource):
    pass


class Displays(_BaseResource):

    @required_acl('dird.displays.read')
    def get(self):
        pass

    @required_acl('dird.displays.create')
    def post(self):
        pass


class Display(_BaseResource):

    @required_acl('dird.displays.{display_uuid}.delete')
    def delete(self, display_uuid):
        pass

    @required_acl('dird.displays.{display_uuid}.read')
    def get(self, display_uuid):
        pass

    @required_acl('dird.displays.{display_uuid}.update')
    def put(self, display_uuid):
        pass
