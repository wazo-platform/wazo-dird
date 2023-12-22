# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, contains, contains_inanyorder, has_entries
from wazo_test_helpers.auth import AuthClient as AuthMock
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import (
    HTTP_404,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.fixtures import http as fixtures

MARIO_INFO = {
    "resourceName": "people/c4084048990019506721",
    "etag": "%Eg0FEEA3CT4BAj0MCz8uGgQCAQcFIgxyV3lrbVp6aVFmRT0=",
    "names": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
            },
            "displayName": "Mario Bros",
            "familyName": "Bros",
            "givenName": "Mario",
            "displayNameLastFirst": "Bros, Mario",
            "unstructuredName": "Mario Bros",
        }
    ],
    "addresses": [
        {
            "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
            "formattedValue": "24 Sussex Dr\\nOttawa, ON K1M 1M4\\nCA",
            "type": "home",
            "formattedType": "Home",
            "streetAddress": "24 Sussex Dr",
            "city": "Ottawa",
            "region": "ON",
            "postalCode": "K1M 1M4",
            "country": "CA",
            "countryCode": "CA",
        },
    ],
    "emailAddresses": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
            },
            "value": "mario@bros.example.com",
            "type": "work",
            "formattedType": "Work",
        }
    ],
    "phoneNumbers": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
            },
            "value": "555-555-1234",
            "type": "work",
            "formattedType": "Work",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "38ad74eb0f67d221"}},
            "value": "555-555-4321",
            "type": "home",
            "formattedType": "Home",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "38ad74eb0f67d221"}},
            "value": "555-555-8888",
            "type": "mobile",
            "formattedType": "Mobile",
        },
    ],
    "biographies": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
            },
            "value": "Notes test",
            "contentType": "TEXT_PLAIN",
        }
    ],
    "organizations": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "38ad74eb0f67d221"},
            },
            "name": "Mushroom Kingdom",
            "title": "Plumber",
        }
    ],
}


LUIGI_INFO = {
    "resourceName": "people/c4537272446000040887",
    "etag": "%Eg0FEEA3CT4BAj0MCz8uGgQCAQcFIgxaV0Zzb2hGVFBGaz0=",
    "names": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "displayName": "Luigi Bros",
            "familyName": "Bros",
            "givenName": "Luigi",
            "displayNameLastFirst": "Bros, Luigi",
            "unstructuredName": "Luigi Bros",
        }
    ],
    "addresses": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "formattedValue": "1600 Pennsylvania Avenue NW\\nWashington, DC 20500\\nUS",
            "type": "work",
            "formattedType": "Work",
            "streetAddress": "1600 Pennsylvania Avenue NW",
            "city": "Washington",
            "region": "DC",
            "postalCode": "20500",
            "country": "US",
            "countryCode": "US",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
            "formattedValue": "24 Sussex Dr\\nOttawa, ON K1M 1M4\\nCA",
            "type": "home",
            "formattedType": "Home",
            "streetAddress": "24 Sussex Dr",
            "city": "Ottawa",
            "region": "ON",
            "postalCode": "K1M 1M4",
            "country": "CA",
            "countryCode": "CA",
        },
    ],
    "emailAddresses": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "value": "luigi_bros@caramail.com",
            "type": "Old",
            "formattedType": "Old",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
            "value": "luigi2@example.com",
            "type": "New",
            "formattedType": "New",
        },
    ],
    "phoneNumbers": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "value": "555-555-4567",
            "type": "home",
            "formattedType": "Home",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
            "value": "555-555-1234",
            "type": "work",
            "formattedType": "Work",
        },
        {
            "metadata": {"source": {"type": "CONTACT", "id": "3ef7a14009000bb7"}},
            "value": "555-555-8888",
            "type": "mobile",
            "formattedType": "Mobile",
        },
    ],
    "biographies": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "value": "Notes user 02",
            "contentType": "TEXT_PLAIN",
        }
    ],
    "organizations": [
        {
            "metadata": {
                "primary": True,
                "source": {"type": "CONTACT", "id": "3ef7a14009000bb7"},
            },
            "name": "Mushroom Kingdom",
            "title": "Plumber",
        }
    ],
}

GOOGLE_CONTACT_LIST = {
    "connections": [MARIO_INFO, LUIGI_INFO],
    "totalPeople": 2,
    "totalItems": 2,
}

GOOGLE_SEARCH_LIST = {
    "results": [{"person": MARIO_INFO}, {"person": LUIGI_INFO}],
    "totalPeople": 2,
    "totalItems": 2,
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
                'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
            },
        )
        self.source_uuid = source['uuid']

        auth_client_mock = AuthMock(host='127.0.0.1', port=auth_port)
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

    @fixtures.google_result(GOOGLE_CONTACT_LIST, GOOGLE_SEARCH_LIST)
    def test_list(self, google_api):
        result = self.list_(self.client, self.source_uuid)
        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(
                    has_entries(
                        name='Mario Bros',
                        firstname='Mario',
                        lastname='Bros',
                        emails=contains_inanyorder(
                            has_entries(address='mario@bros.example.com', label='work'),
                        ),
                        numbers=contains_inanyorder(
                            '5555551234', '5555558888', '5555554321'
                        ),
                        numbers_by_label=has_entries(
                            home='5555554321', mobile='5555558888', work='5555551234'
                        ),
                        organizations=contains_inanyorder(
                            has_entries(name='Mushroom Kingdom', title='Plumber'),
                        ),
                        addresses=contains_inanyorder(
                            has_entries(
                                address='24 Sussex Dr\\nOttawa, ON K1M 1M4\\nCA',
                                label='home',
                            ),
                        ),
                        note='Notes test',
                    ),
                    has_entries(
                        name='Luigi Bros',
                        emails=contains_inanyorder(
                            has_entries(address='luigi2@example.com', label='New'),
                            has_entries(address='luigi_bros@caramail.com', label='Old'),
                        ),
                        numbers=contains_inanyorder(
                            '5555551234', '5555558888', '5555554567'
                        ),
                        numbers_by_label=has_entries(
                            work='5555551234',
                            home='5555554567',
                            mobile='5555558888',
                        ),
                        note='Notes user 02',
                    ),
                ),
                total=2,
                filtered=2,
            ),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST, GOOGLE_SEARCH_LIST)
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

    @fixtures.google_result(GOOGLE_CONTACT_LIST, GOOGLE_SEARCH_LIST)
    def test_search(self, google_api):
        self.list_(self.client, self.source_uuid, search='mario'),
        google_api.verify(
            {
                'method': 'GET',
                'path': '/v1/people:searchContacts',
                'headers': {'Authorization': ['Bearer an-access-token']},
            }
        )

    def list_(self, client, *args, **kwargs):
        return client.backends.list_contacts_from_source('google', *args, **kwargs)
