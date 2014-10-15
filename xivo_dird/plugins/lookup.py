# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
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

from flask_restful.utils.cors import crossdomain
from flask_restplus.resource import Resource
from xivo_dird import BaseServicePlugin

API_VERSION = '0.1'


def _assert_has_args(args, *expected_args):
    for arg in expected_args:
        if arg not in args:
            raise ValueError('Missing %s argument in %s' % (arg, args))


class LookupServicePlugin(BaseServicePlugin):

    lookup_url = '/lookup/<profile>'

    def load(self, args=None):
        if not args:
            args = {}

        _assert_has_args(args, 'http_app', 'api_namespace', 'rest_api')

        self._setup_http_app(args['http_app'], args['api_namespace'], args['rest_api'])

    def unload(self, args=None):
        pass

    def _setup_http_app(self, http_app, api_namespace, rest_api):

        @crossdomain(origin='*')
        @api_namespace.route(self.lookup_url)
        class Lookup(Resource):

            parser = rest_api.parser()
            parser.add_argument('term', type=str, required=True,
                                help='Search a given term in all configured sources')

            @rest_api.doc(parser=parser)
            def get(cls, profile):
                pass
