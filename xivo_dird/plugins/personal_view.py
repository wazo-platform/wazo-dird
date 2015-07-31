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
from time import time

from xivo_dird import BaseViewPlugin
from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)


class PersonalViewPlugin(BaseViewPlugin):

    personal_all_url = '/personal'
    personal_one_url = '/personal/<contact_id>'

    def load(self, args=None):
        personal_service = args['services'].get('personal')
        if personal_service:
            PersonalAll.configure(personal_service)
            PersonalOne.configure(personal_service)
            api.add_resource(PersonalAll, self.personal_all_url)
            api.add_resource(PersonalOne, self.personal_one_url)


class PersonalAll(AuthResource):

    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    def post(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        contact = request.json
        contact = self.personal_service.create_contact(contact, token_infos)
        return contact, 201

    def get(self):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        result = {'items': self.personal_service.list_contacts_raw(token_infos)}
        return result, 200


class PersonalOne(AuthResource):

    personal_service = None

    @classmethod
    def configure(cls, personal_service):
        cls.personal_service = personal_service

    def put(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        new_contact = request.json
        try:
            contact = self.personal_service.edit_contact(contact_id, new_contact, token_infos)
            return contact, 200
        except self.personal_service.NoSuchPersonalContact as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

    def delete(self, contact_id):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        try:
            self.personal_service.remove_contact(contact_id, token_infos)
            return '', 204
        except self.personal_service.NoSuchPersonalContact as e:
            error = {
                'reason': [str(e)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404
