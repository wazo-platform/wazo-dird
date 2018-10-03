# -*- coding: utf-8 -*-
# Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from flask import request
from flask import Response
from flask import render_template
from flask_restful.inputs import natural
from flask_restful import reqparse
from time import time

from wazo_dird.auth import required_acl
from wazo_dird.exception import ProfileNotFoundError
from wazo_dird.rest_api import AuthResource

logger = logging.getLogger(__name__)


def _error(code, msg):
    return {'reason': [msg],
            'timestamp': [time()],
            'status_code': code}, code


class PhoneMenu(AuthResource):

    def __init__(self, template, content_type):
        self.template = template
        self.content_type = content_type

    @required_acl('dird.directories.menu.{profile}.{xivo_user_uuid}.read')
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

    @required_acl('dird.directories.input.{profile}.{xivo_user_uuid}.read')
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

    @required_acl('dird.directories.lookup.{profile}.{xivo_user_uuid}.read')
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
                                       total=results['total'],
                                       offset=results['offset'],
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
