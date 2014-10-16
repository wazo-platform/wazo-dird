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
from stevedore import enabled
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

        _assert_has_args(args, 'http_app', 'api_namespace', 'rest_api', 'config')

        self._setup_http_app(args['http_app'], args['api_namespace'], args['rest_api'])
        self._service = _LookupService(args['config'])

    def unload(self, args=None):
        pass

    def _setup_http_app(self, http_app, api_namespace, rest_api):

        @crossdomain(origin='*')
        @api_namespace.route(self.lookup_url)
        class Lookup(Resource):

            parser = rest_api.parser()
            parser.add_argument('term', type=str, required=True,
                                help='Search a given term in all configured sources')
            parser.add_argument('user_id', type=str, required=False,
                                help='The user doing the query')

            @rest_api.doc(parser=parser)
            def get(cls, profile):
                args = cls.parser.parse_args()
                return self._service.lookup(args['term'], profile, args.get('user_id'))


class _LookupService(object):

    def __init__(self, config):
        self._config = config
        self._source_manager = _SourceManager(config)

    def lookup(self, term, profile, user_id):
        args = {'user_id': user_id}

        for source, columns in self._source_manager.get_by_profile(profile):
            for result in source.search(term, args, columns):
                yield result


class _SourceManager(object):

    _namespace = 'xivo-dird.backends'

    def __init__(self, config):
        self._config = config

    def should_load_backend(self, extension):
        return extension.name in self._config.get('source_plugins', [])

    def load_backends(self):
        manager = enabled.EnabledExtensionManager(
            namespace=self._namespace,
            check_func=self.should_load_backend,
            invoke_on_load=False,
        )

    def get_by_profile(self):
        '''
        generates a list of source, column pairs
        '''
        return
