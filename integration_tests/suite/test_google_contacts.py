# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, contains, contains_inanyorder, has_entries

from xivo_test_helpers.auth import AuthClient as AuthMock
from xivo_test_helpers.hamcrest.raises import raises

from .helpers.constants import (
    HTTP_404,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.base import BaseDirdIntegrationTest
from .helpers.fixtures import http as fixtures

GOOGLE_CONTACT_LIST = {
    "feed": {
        "openSearch$totalResults": {"$t": "2"},
        "openSearch$startIndex": {"$t": "1"},
        "openSearch$itemsPerPage": {"$t": "10000"},
        "entry": [
            {
                "id": {
                    "$t": "http://www.google.com/m8/feeds/contacts/peach%40bros.example.com/base/20aec7728b4f316b"
                },
                "title": {"$t": "Mario Brös", "type": "text"},
                "gd$name": {
                    "gd$fullName": {"$t": "Mario Bros"},
                    "gd$givenName": {"$t": "Mario"},
                    "gd$familyName": {"$t": "Bros"},
                },
                "gd$organization": [
                    {
                        "rel": "http://schemas.google.com/g/2005#other",
                        "gd$orgTitle": {"$t": "Artist"},
                        "gd$orgName": {"$t": "MarioLand"},
                    }
                ],
                "gd$email": [
                    {
                        "address": "mario@bros.example.com",
                        "rel": "http://schemas.google.com/g/2005#other",
                    }
                ],
                "gd$phoneNumber": [
                    {
                        "rel": "http://schemas.google.com/g/2005#mobile",
                        "uri": "tel:+1-555-555-1234",
                        "$t": "+1 555-555-1234",
                    },
                    {
                        "rel": "http://schemas.google.com/g/2005#home",
                        "uri": "tel:+1-555-555-1111",
                        "$t": "+1 5555551111",
                    },
                ],
                "gd$structuredPostalAddress": [
                    {
                        "rel": "http://schemas.google.com/g/2005#home",
                        "gd$formattedAddress": {"$t": "Main Land"},
                    },
                    {
                        "label": "Second address",
                        "gd$formattedAddress": {"$t": "Alternative Land"},
                    },
                ],
            },
            {
                "id": {
                    "$t": "http://www.google.com/m8/feeds/contacts/peach%40bros.example.com/base/72b6b4840bf772e6"
                },
                "title": {"$t": "Luigi Bros", "type": "text"},
                "gd$email": [
                    {
                        "address": "Luigi@bros.example.com",
                        "rel": "http://schemas.google.com/g/2005#home",
                    },
                    {"address": "luigi_bros@caramail.com", "label": "Old school"},
                ],
                "gd$phoneNumber": [
                    {
                        "rel": "http://schemas.google.com/g/2005#mobile",
                        "uri": "tel:+1-555-555-4567",
                        "$t": "+1 555-555-4567",
                    },
                    {
                        "rel": "http://schemas.google.com/g/2005#home",
                        "uri": "tel:+1-555-555-1111",
                        "$t": "+1 5555551111",
                    },
                    {
                        "label": "Mushroom land land-line",
                        "uri": "tel:+1-555-555-2222",
                        "$t": "(555) 555-2222",
                    },
                ],
            },
        ],
    }
}


GOOGLE_GROUP_LIST = {
    "feed": {
        "entry": [
            {
                "id": {
                    "$t": "http://www.google.com/m8/feeds/groups/peach%40bros.example.com/base/6"
                },
                "gContact$systemGroup": {"id": "Contacts"},
            },
        ],
    }
}


class BaseGoogleAssetTestCase(BaseDirdIntegrationTest):

    GOOGLE_EXTERNAL_AUTH = {
        "access_token": "an-access-token",
        "scope": "a-scope",
        "token_expiration": 42,
    }


class TestGoogleContactList(BaseGoogleAssetTestCase):

    asset = 'dird_google'

    def setUp(self):
        super().setUp()
        auth_port = self.service_port(9497, 'auth')
        source = self.client.backends.create_source(
            'google',
            {
                'name': 'google',
                'auth': {'host': 'auth', 'port': 9497, 'verify_certificate': False},
            },
        )
        self.source_uuid = source['uuid']

        auth_client_mock = AuthMock(host='localhost', port=auth_port)
        auth_client_mock.set_external_auth(self.GOOGLE_EXTERNAL_AUTH)

    def tearDown(self):
        self.client.backends.delete_source('google', self.source_uuid)
        super().tearDown()

    def test_unknown_source(self):
        assert_that(
            calling(self.list_).with_args(self.client, UNKNOWN_UUID),
            raises(Exception).matching(HTTP_404),
        )

    @fixtures.google_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.google_source(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub, main):
        main_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(self.list_).with_args(sub_client, main['uuid']),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(self.list_).with_args(
                main_client, main['uuid'], tenant_uuid=SUB_TENANT
            ),
            raises(Exception).matching(HTTP_404),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST)
    def test_list(self, google_api):
        result = self.list_(self.client, self.source_uuid)
        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(
                    has_entries(
                        name='Mario Bros',
                        emails=contains_inanyorder('mario@bros.example.com'),
                        firstname='Mario',
                        lastname='Bros',
                        numbers=contains_inanyorder('+15555551111', '+15555551234'),
                        numbers_by_label=has_entries(
                            home='+15555551111', mobile='+15555551234'
                        ),
                        organizations=contains_inanyorder(
                            has_entries(name='MarioLand', title='Artist'),
                        ),
                        addresses=contains_inanyorder(
                            has_entries(address='Main Land', label='home'),
                            has_entries(address='Alternative Land', label='Second address'),
                        ),
                    ),
                    has_entries(
                        name='Luigi Bros',
                        emails=contains_inanyorder(
                            'Luigi@bros.example.com', 'luigi_bros@caramail.com'
                        ),
                        numbers=contains_inanyorder(
                            '5555552222', '+15555551111', '+15555554567'
                        ),
                        numbers_by_label=has_entries(
                            'Mushroom land land-line',
                            '5555552222',
                            'home',
                            '+15555551111',
                            'mobile',
                            '+15555554567',
                        ),
                    ),
                ),
                total=2,
                filtered=2,
            ),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST)
    def test_pagination(self, google_api):
        mario = has_entries(name='Mario Bros')
        luigi = has_entries(name='Luigi Bros')

        assert_that(
            self.list_(self.client, self.source_uuid, order='name'),
            has_entries(items=contains(luigi, mario)),
        )

        assert_that(
            self.list_(self.client, self.source_uuid, order='name', direction='desc'),
            has_entries(items=contains(mario, luigi)),
        )

        assert_that(
            self.list_(self.client, self.source_uuid, order='name', limit=1),
            has_entries(items=contains(luigi)),
        )

        assert_that(
            self.list_(self.client, self.source_uuid, order='name', offset=1),
            has_entries(items=contains(mario)),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST, GOOGLE_GROUP_LIST)
    def test_search(self, google_api):
        self.list_(self.client, self.source_uuid, search='mario'),
        google_api.verify(
            {
                'method': 'GET',
                'path': '/m8/feeds/groups/default/full',
                'headers': {'Authorization': ['Bearer an-access-token']},
            }
        )
        google_api.verify(
            {
                'method': 'GET',
                'path': '/m8/feeds/contacts/default/full',
                'headers': {'Authorization': ['Bearer an-access-token']},
                'queryStringParameters': {
                    'q': ['mario'],
                    'group': [
                        'http://www.google.com/m8/feeds/groups/peach%40bros.example.com/base/6',
                    ],
                },
            }
        )

    def list_(self, client, *args, **kwargs):
        return client.backends.list_contacts_from_source('google', *args, **kwargs)
