# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains,
    contains_string,
    has_entries,
)
from wazo_dird_client import Client as DirdClient

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN, VALID_TOKEN_NO_ACL


class TestGraphQL(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def test_authentication(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None
        token = None

        # Wrong token
        response = dird.graphql.query(query, tenant_uuid, token)
        assert_that(
            response['errors'],
            contains(has_entries({'path': ['hello'], 'message': 'Unauthorized'})),
        )

        # Token without ACL
        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN_NO_ACL)
        assert_that(
            response['errors'],
            contains(has_entries({'path': ['hello'], 'message': 'Unauthorized'})),
        )

        # Valid token
        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)
        assert response == {'data': {'hello': 'world'}}

    def test_hello_world(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None

        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)

        assert response == {'data': {'hello': 'world'}}


class TestGraphQLNoAuth(BaseDirdIntegrationTest):

    asset = 'no_auth_server'

    def test_unreachable_auth_should_return_error(self):
        dird = DirdClient(
            'localhost', self.service_port(9489, 'dird'), verify_certificate=False
        )
        query = {'query': '{ hello }'}
        tenant_uuid = None

        response = dird.graphql.query(query, tenant_uuid, VALID_TOKEN)
        assert_that(
            response['errors'],
            contains(
                has_entries(
                    {'path': ['hello'], 'message': contains_string('unreachable')}
                )
            ),
        )
