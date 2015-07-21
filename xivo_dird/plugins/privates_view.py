# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import logging

from flask import request

from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)


class PrivatesViewPlugin(BaseViewPlugin):

    private_all_url = '/privates'
    private_one_url = '/privates/<contact_id>'

    def load(self, args=None):
        privates_service = args['services'].get('privates')
        PrivateAll.configure(privates_service)
        PrivateOne.configure(privates_service)
        api.add_resource(PrivateAll, self.private_all_url)
        api.add_resource(PrivateOne, self.private_one_url)


class PrivateAll(AuthResource):

    privates_service = None

    @classmethod
    def configure(cls, privates_service):
        cls.privates_service = privates_service

    def post(self):
        contact = request.json
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        contact = self.privates_service.create_contact(contact, token_infos)
        return contact, 201

    def get(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        result = {'items': self.privates_service.list_contacts_raw(token_infos)}
        return result, 200


class PrivateOne(AuthResource):

    privates_service = None

    @classmethod
    def configure(cls, privates_service):
        cls.privates_service = privates_service

    def delete(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        self.privates_service.remove_contact(contact_id, token_infos)
        return '', 204
