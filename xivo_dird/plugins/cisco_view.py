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

from xivo_dird.core import auth
from xivo_dird.core.auth import AuthResource
from xivo_dird import BaseViewPlugin
from xivo_dird.core.phone_helpers import PhoneDisplay
from xivo_dird.core.rest_api import api

logger = logging.getLogger(__name__)

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_FOLDER = os.path.join(CURRENT_PATH, 'lookup_templates')
TEMPLATE_CISCO_MENU = "cisco_menu.jinja"
TEMPLATE_CISCO_NO_TERM = "cisco_no_term.jinja"
TEMPLATE_CISCO_RESULTS = "cisco_results.jinja"


class CiscoViewPlugin(BaseViewPlugin):

    cisco_lookup_menu = '/directories/menu/<profile>/cisco'
    cisco_lookup = '/directories/lookup/<profile>/cisco'

    def load(self, args=None):
        phone_display = PhoneDisplay.new_from_config(args['config'])
        jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))

        lookup_service = args['services'].get('lookup')
        if lookup_service:
            CiscoLookupMenu.configure(lookup_service, jinja_env)
            CiscoLookup.configure(lookup_service, jinja_env, phone_display)
            api.add_resource(CiscoLookupMenu, self.cisco_lookup_menu)
            api.add_resource(CiscoLookup, self.cisco_lookup)


class CiscoLookupMenu(AuthResource):

    jinja_env = None
    lookup_service = None

    @classmethod
    def configure(cls, lookup_service, jinja_env):
        cls.lookup_service = lookup_service
        cls.jinja_env = jinja_env

    def get(self, profile):
        proxy_url = request.headers.get('Proxy-URL', None)
        if not proxy_url:
            proxy_url = request.base_url.replace('menu', 'lookup', 1)

        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        xivo_user_uuid = token_infos['xivo_user_uuid']

        template = self.jinja_env.get_template(TEMPLATE_CISCO_MENU)
        context = {'xivo_proxy_url': proxy_url,
                   'xivo_user_uuid': xivo_user_uuid}
        response_xml = template.render(context)

        return Response(response_xml, content_type='text/xml', status=200)


parser = reqparse.RequestParser()
parser.add_argument('term', type=unicode, required=False, location='args')


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
        term = args.get('term', None)
        if not term:
            template = self.jinja_env.get_template(TEMPLATE_CISCO_NO_TERM)
            context = {'xivo_proxy_url': proxy_url,
                       'xivo_user_uuid': xivo_user_uuid}
            response_xml = template.render(context)

            return Response(response_xml, content_type='text/xml', mimetype='text/xml', status=200)

        lookup_results = self.lookup_service.lookup(term, profile, args={}, token_infos=token_infos)

        template = self.jinja_env.get_template(TEMPLATE_CISCO_RESULTS)
        context = {
            'results': lookup_results,
            'name_field': self.phone_display.get_name_field(profile),
            'number_field': self.phone_display.get_number_field(profile),
        }
        response_xml = template.render(context)

        return Response(response_xml, content_type='text/xml', status=200)
