# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from .helpers.base import BaseDirdIntegrationTest

from wazo_dird_client import Client as DirdClient


class TestGraphQL(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def test_hello_world(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None
        token = None

        response = dird.graphql.query(query, tenant_uuid, token)

        assert response == {'data': {'hello': 'world'}}
