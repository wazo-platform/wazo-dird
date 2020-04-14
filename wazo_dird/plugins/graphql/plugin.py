# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask_graphql import GraphQLView
from wazo_dird import BaseViewPlugin
from wazo_dird import rest_api

from .resolver import Resolver
from .schema import make_schema


class GraphQLViewPlugin(BaseViewPlugin):
    def load(self, dependencies):
        app = dependencies['flask_app']
        resolver = Resolver()
        schema = make_schema(resolver)

        app.add_url_rule(
            '/{version}/graphql'.format(version=rest_api.VERSION),
            view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True),
        )
