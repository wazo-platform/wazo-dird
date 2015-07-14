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
from xivo_dird.core.auth import AuthResource
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)


class PrivatesViewPlugin(BaseViewPlugin):

    private_all_url = '/privates'
    private_one_url = '/privates/<contact_id>'

    def load(self, args=None):
        api.add_resource(PrivateAll, self.private_all_url)


class PrivateAll(AuthResource):

    contacts = []

    def post(self):
        contact = request.json
        self.contacts.append(contact)
        return contact, 201

    def get(self):
        result = {'items': self.contacts}
        return result, 200
