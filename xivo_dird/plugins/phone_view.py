# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Avencall
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
from flask import Response
from flask import render_template
from flask_restful.inputs import natural
from flask_restful import reqparse
from time import time

from xivo_dird.core.auth import required_acl
from xivo_dird.core.exception import ProfileNotFoundError
from xivo_dird.core.rest_api import AuthResource

logger = logging.getLogger(__name__)


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time()],
            'status_code': code}, code


class PhoneMenu(AuthResource):

    def __init__(self, template, content_type):
        self.template = template
        self.content_type = content_type

    @required_acl('dird.directories.menu.{profile}.{xivo_user_uuid}')
    def get(self, profile, xivo_user_uuid):
        proxy_url = request.headers.get('Proxy-URL', _build_next_url('menu'))

        response_xml = render_template(self.template,
                                       xivo_proxy_url=proxy_url,
                                       xivo_user_uuid=xivo_user_uuid)

        return Response(response_xml, content_type=self.content_type, status=200)


class PhoneInput(AuthResource):

    def __init__(self, template, content_type):
        self.template = template
        self.content_type = content_type

    @required_acl('dird.directories.input.{profile}.{xivo_user_uuid}')
    def get(self, profile, xivo_user_uuid):
        proxy_url = request.headers.get('Proxy-URL', _build_next_url('input'))

        response_xml = render_template(self.template,
                                       xivo_proxy_url=proxy_url,
                                       xivo_user_uuid=xivo_user_uuid)

        return Response(response_xml, content_type=self.content_type, status=200)


class PhoneLookup(AuthResource):

    def __init__(self, template, content_type, phone_lookup_service, max_item_per_page=None):
        self.template = template
        self.content_type = content_type
        self.phone_lookup_service = phone_lookup_service

        self.parser = reqparse.RequestParser()
        self.parser.add_argument('limit', type=natural, required=False, default=max_item_per_page, location='args')
        self.parser.add_argument('offset', type=natural, required=False, default=0, location='args')
        self.parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')

    @required_acl('dird.directories.lookup.{profile}.{xivo_user_uuid}')
    def get(self, profile, xivo_user_uuid):
        args = self.parser.parse_args()
        term = args['term']
        offset = args['offset']
        limit = args['limit']
        proxy_url = request.headers.get('Proxy-URL', _build_next_url('lookup'))
        token = request.headers['X-Auth-Token']

        try:
            results = self.phone_lookup_service.lookup(term,
                                                       profile,
                                                       xivo_user_uuid=xivo_user_uuid,
                                                       token=token,
                                                       limit=limit,
                                                       offset=offset)
        except ProfileNotFoundError:
            logger.warning('phone lookup failed: unknown profile %r', profile)
            return _error(404, 'The profile `{profile}` does not exist'.format(profile=profile))

        response_xml = render_template(self.template,
                                       results=results['results'],
                                       xivo_proxy_url=proxy_url,
                                       xivo_user_uuid=xivo_user_uuid,
                                       term=term,
                                       limit=limit,
                                       offset_next=results['next_offset'],
                                       offset_previous=results['previous_offset'])

        return Response(response_xml, content_type=self.content_type, status=200)


def _build_next_url(current):
    if current == 'menu':
        return request.base_url.replace('menu', 'input', 1)
    if current == 'input':
        return request.base_url.replace('input', 'lookup', 1)
    if current == 'lookup':
        return request.base_url
    return None
