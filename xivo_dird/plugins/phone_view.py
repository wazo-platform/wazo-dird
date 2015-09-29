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
from flask import Response
from flask_restful import reqparse
from time import time

from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource

logger = logging.getLogger(__name__)


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time()],
            'status_code': code}, code


class PhoneMenu(AuthResource):

    lookup_service = None

    @classmethod
    def configure(cls, lookup_service):
        cls.lookup_service = lookup_service

    def __init__(self, template, content_type):
        self.template = template
        self.content_type = content_type

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url.replace('menu', 'input', 1)

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        context = {'xivo_proxy_url': proxy_url,
                   'xivo_user_uuid': xivo_user_uuid}
        response_xml = self.template.render(context)

        return Response(response_xml, content_type=self.content_type, status=200)


class PhoneInput(AuthResource):

    lookup_service = None

    @classmethod
    def configure(cls, lookup_service):
        cls.lookup_service = lookup_service

    def __init__(self, template, content_type):
        self.template = template
        self.content_type = content_type

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url.replace('input', 'lookup', 1)

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        context = {'xivo_proxy_url': proxy_url,
                   'xivo_user_uuid': xivo_user_uuid}
        response_xml = self.template.render(context)

        return Response(response_xml, content_type=self.content_type, status=200)


parser = reqparse.RequestParser()
parser.add_argument('limit', type=int, required=False, help='limit cannot be converted', location='args')
parser.add_argument('offset', type=int, required=False, help='offset cannot be converted', location='args')
parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')


class PhoneLookup(AuthResource):

    lookup_service = None
    phone_display = None

    @classmethod
    def configure(cls, lookup_service, phone_display):
        cls.lookup_service = lookup_service
        cls.phone_display = phone_display

    def __init__(self, template, content_type, max_item_per_page=None):
        self.template = template
        self.content_type = content_type
        self.max_item_per_page = max_item_per_page

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        args = parser.parse_args()
        term = args['term']
        limit = self.max_item_per_page if args['limit'] is None else args['limit']
        offset = 0 if args['offset'] is None else args['offset']

        if limit < 0 and limit is not None:
            return _error(400, 'The limit should be positive')
        if offset < 0:
            return _error(400, 'The offset should be positive')

        transform_func = self.phone_display.get_transform_function(profile)
        results = self.lookup_service.lookup2(term, profile, args={}, token_infos=token_infos,
                                              limit=limit, offset=offset, transform_func=transform_func)

        context = {
            'results': results['results'],
            'xivo_proxy_url': proxy_url,
            'xivo_user_uuid': xivo_user_uuid,
            'term': term,
            'limit': limit,
            'offset_next': results['next_offset'],
            'offset_previous': results['previous_offset']
        }
        response_xml = self.template.render(context)

        return Response(response_xml, content_type=self.content_type, status=200)
