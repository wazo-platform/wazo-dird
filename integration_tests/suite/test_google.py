# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from hamcrest import assert_that, contains, has_entries, has_item

from xivo_test_helpers.auth import AuthClient as AuthMock

from .helpers.base import BaseDirdIntegrationTest
from .helpers.fixtures import http as fixtures

requests.packages.urllib3.disable_warnings()

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


class TestGooglePlugin(BaseDirdIntegrationTest):

    asset = 'dird_google'
    GOOGLE_EXTERNAL_AUTH = {
        "access_token": "an-access-token",
        "scope": "a-scope",
        "token_expiration": 42,
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        client = cls.get_client()
        source_body = {
            'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
            'first_matched_columns': ['numbers'],
            'format_columns': {
                'phone_mobile': '{numbers_by_label[mobile]}',
                'phone': '{numbers[0]}',
                'email': '{emails[0][address]}',
                'reverse': '{name}',
            },
            'name': 'google',
            'searched_columns': ["name", "emails", "numbers"],
        }
        display_body = {
            'name': 'default',
            'columns': [
                {'title': 'name', 'field': 'name'},
                {'title': 'email', 'field': 'email'},
                {'title': 'number', 'field': 'phone'},
                {'title': 'mobile', 'field': 'phone_mobile'},
            ],
        }
        display = client.displays.create(display_body)
        source = client.backends.create_source('google', source_body)

        profile_body = {
            'name': 'default',
            'display': display,
            'services': {
                'lookup': {'sources': [source]},
                'reverse': {'sources': [source]},
                'favorites': {'sources': [source]},
            },
        }
        profile = client.profiles.create(profile_body)

        cls.source_uuid = source['uuid']
        cls.display_uuid = display['uuid']
        cls.profile_uuid = profile['uuid']

        cls.auth_client_mock = AuthMock(
            host='0.0.0.0', port=cls.service_port(9497, 'auth')
        )
        cls.auth_client_mock.set_external_auth(cls.GOOGLE_EXTERNAL_AUTH)

    @classmethod
    def tearDownClass(cls):
        client = cls.get_client()
        cls.auth_client_mock.reset_external_auth()
        client.backends.delete_source('google', cls.source_uuid)
        client.displays.delete(cls.display_uuid)
        client.profiles.delete(cls.profile_uuid)
        super().tearDownClass()

    @fixtures.google_result(GOOGLE_CONTACT_LIST)
    def test_plugin_lookup(self, google_api):
        result = self.client.directories.lookup(term='mario', profile='default')

        assert_that(
            result,
            has_entries(
                results=contains(
                    has_entries(
                        backend='google',
                        source='google',
                        column_values=contains(
                            'Mario Bros',
                            'mario@bros.example.com',
                            '5555551234',
                            '5555558888',
                        ),
                    )
                )
            ),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST)
    def test_plugin_favorites(self, google_api):
        response = self.client.directories.lookup(term='luigi', profile='default')
        luigi = response['results'][0]
        source = luigi['source']
        id_ = luigi['relations']['source_entry_id']

        self.client.directories.new_favorite(source, id_)

        result = self.client.directories.favorites(profile='default')
        assert_that(
            result,
            has_entries(
                results=contains(has_entries(column_values=has_item('Luigi Bros')))
            ),
        )

    @fixtures.google_result(GOOGLE_CONTACT_LIST)
    def test_plugin_reverse(self, google_api):
        response = self.client.directories.reverse(
            exten='5555551234', profile='default', user_uuid='uuid-tenant-master'
        )

        assert_that(response, has_entries(display='Mario Bros'))
