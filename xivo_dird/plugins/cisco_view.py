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

import os
import logging

from flask import request
from flask import Response
from flask_restful import reqparse
from jinja2 import FileSystemLoader
from jinja2 import Environment
from time import time

from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource
from xivo_dird import BaseViewPlugin
from xivo_dird.core.rest_api import api
from xivo_dird.plugins.phone_helpers import new_phone_display_from_config

logger = logging.getLogger(__name__)

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_FOLDER = os.path.join(CURRENT_PATH, 'lookup_templates')
TEMPLATE_CISCO_MENU = "cisco_menu.jinja"
TEMPLATE_CISCO_INPUT = "cisco_input.jinja"
TEMPLATE_CISCO_RESULTS = "cisco_results.jinja"

MAX_ITEM_PER_PAGE = 16


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time()],
            'status_code': code}, code


class CiscoViewPlugin(BaseViewPlugin):

    cisco_menu = '/directories/menu/<profile>/cisco'
    cisco_input = '/directories/input/<profile>/cisco'
    cisco_lookup = '/directories/lookup/<profile>/cisco'

    def load(self, args=None):
        phone_display = new_phone_display_from_config(args['config'])
        jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

        lookup_service = args['services'].get('lookup')
        if lookup_service:
            CiscoMenu.configure(lookup_service, jinja_env)
            CiscoInput.configure(lookup_service, jinja_env)
            CiscoLookup.configure(lookup_service, jinja_env, phone_display)
            api.add_resource(CiscoMenu, self.cisco_menu)
            api.add_resource(CiscoInput, self.cisco_input)
            api.add_resource(CiscoLookup, self.cisco_lookup)


class CiscoMenu(AuthResource):

    jinja_env = None
    lookup_service = None

    @classmethod
    def configure(cls, lookup_service, jinja_env):
        cls.lookup_service = lookup_service
        cls.jinja_env = jinja_env

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url.replace('menu', 'input', 1)

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        template = self.jinja_env.get_template(TEMPLATE_CISCO_MENU)
        context = {'xivo_proxy_url': proxy_url,
                   'xivo_user_uuid': xivo_user_uuid}
        response_xml = template.render(context)

        return Response(response_xml, content_type='text/xml', status=200)


class CiscoInput(AuthResource):

    jinja_env = None
    lookup_service = None

    @classmethod
    def configure(cls, lookup_service, jinja_env):
        cls.lookup_service = lookup_service
        cls.jinja_env = jinja_env

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url.replace('input', 'lookup', 1)

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        template = self.jinja_env.get_template(TEMPLATE_CISCO_INPUT)
        context = {'xivo_proxy_url': proxy_url,
                   'xivo_user_uuid': xivo_user_uuid}
        response_xml = template.render(context)

        return Response(response_xml, content_type='text/xml', status=200)


parser = reqparse.RequestParser()
parser.add_argument('limit', type=int, required=False, help='limit cannot be converted', location='args')
parser.add_argument('offset', type=int, required=False, help='offset cannot be converted', location='args')
parser.add_argument('term', type=unicode, required=True, help='term is missing', location='args')


class CiscoLookup(AuthResource):

    jinja_env = None
    lookup_service = None
    phone_display = None

    @classmethod
    def configure(cls, lookup_service, jinja_env, phone_display):
        cls.lookup_service = lookup_service
        cls.jinja_env = jinja_env
        cls.phone_display = phone_display

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        args = parser.parse_args()
        term = args['term']
        limit = MAX_ITEM_PER_PAGE if args['limit'] is None else args['limit']
        offset = 0 if args['offset'] is None else args['offset']

        if limit < 0:
            return _error(400, 'The limit should be positive')
        if offset < 0:
            return _error(400, 'The offset should be positive')

        transform_func = self.phone_display.get_transform_function(profile)
        results = self.lookup_service.lookup2(term, profile, args={}, token_infos=token_infos,
                                              limit=limit, offset=offset, transform_func=transform_func)

        template = self.jinja_env.get_template(TEMPLATE_CISCO_RESULTS)
        context = {
            'results': results['results'],
            'xivo_proxy_url': proxy_url,
            'xivo_user_uuid': xivo_user_uuid,
            'term': term,
            'limit': limit,
            'offset_next': results['next_offset'],
            'offset_previous': results['previous_offset']
        }
        response_xml = template.render(context)

        return Response(response_xml, content_type='text/xml', status=200)
