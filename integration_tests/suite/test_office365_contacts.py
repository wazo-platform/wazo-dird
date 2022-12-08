# Copyright 2020-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    has_entries,
    has_item,
)

from wazo_test_helpers.auth import AuthClient as AuthMock
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.constants import (
    HTTP_404,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.base import BaseDirdIntegrationTest
from .helpers.fixtures import http as fixtures


OFFICE365_CONTACT_LIST = {
    "value": [
        {
            "id": "an-id",
            "displayName": "Mario Bros",
            "givenName": "Mario",
            "surname": "Bros",
            "mobilePhone": "",
            "businessPhones": ['7777777777'],
            "emailAddresses": [{"address": "mbros@wazoquebec.onmicrosoft.com"}],
        },
        {
            "id": "another-id",
            "displayName": "Luigi Bros",
            "givenName": "Luigi",
            "surname": "Bros",
            "mobilePhone": "",
            "businessPhones": ['5555555555'],
            "emailAddresses": [{"address": "lbros@wazoquebec.onmicrosoft.com"}],
        },
    ]
}

PAGED_OFFICE365_CONTACTS_LIST = [
    {
        "value": [
            {
                "id": f"an-id-{i}",
                "displayName": f"displayName-{i}",
                "givenName": f"givenName-{i}",
                "surname": f"surname-{i}",
                "mobilePhone": "",
                "businessPhones": ['7777777777'],
                "emailAddresses": [
                    {"address": f"email-{i}@wazoquebec.onmicrosoft.com"}
                ],
            }
            for i in range(1000)
        ],
        '@odata.nextLink': 'http://microsoft.com:443/v1.0/me/contacts/path1',
        'endpoint': '/v1.0/me/contacts',
    },
    {
        "value": [
            {
                "id": f"an-id-{i}",
                "displayName": f"displayName-{i}",
                "givenName": f"givenName-{i}",
                "surname": f"surname-{i}",
                "mobilePhone": "",
                "businessPhones": ['7777777777'],
                "emailAddresses": [
                    {"address": f"email-{i}@wazoquebec.onmicrosoft.com"}
                ],
            }
            for i in range(1000, 2000)
        ],
        '@odata.nextLink': 'http://microsoft.com:443/v1.0/me/contacts/path2',
        'endpoint': '/v1.0/me/contacts/path1',
    },
    {
        "value": [
            {
                "id": f"an-id-{i}",
                "displayName": f"displayName-{i}",
                "givenName": f"givenName-{i}",
                "surname": f"surname-{i}",
                "mobilePhone": "",
                "businessPhones": ['7777777777'],
                "emailAddresses": [
                    {"address": f"email-{i}@wazoquebec.onmicrosoft.com"}
                ],
            }
            for i in range(2000, 5000)
        ],
        'endpoint': '/v1.0/me/contacts/path2',
    },
]


class BaseOffice365AssetTestCase(BaseDirdIntegrationTest):

    OFFICE365_EXTERNAL_AUTH = {
        "access_token": "an-access-token",
        "scope": "a-scope",
        "token_expiration": 42,
    }


class TestOffice365ContactList(BaseOffice365AssetTestCase):

    asset = 'dird_microsoft'

    def setUp(self):
        super().setUp()
        auth_port = self.service_port(9497, 'auth')
        source = self.client.backends.create_source(
            'office365',
            {
                'name': 'office365',
                'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
                'endpoint': 'http://microsoft.com:443/v1.0/me/contacts',
            },
        )
        self.source_uuid = source['uuid']

        auth_client_mock = AuthMock(host='127.0.0.1', port=auth_port)
        auth_client_mock.set_external_auth(self.OFFICE365_EXTERNAL_AUTH)

    def tearDown(self):
        self.client.backends.delete_source('office365', self.source_uuid)
        super().tearDown()

    def test_unknown_source(self):
        assert_that(
            calling(self.list_).with_args(self.client, UNKNOWN_UUID),
            raises(Exception).matching(HTTP_404),
        )

    @fixtures.office365_paginated_result(PAGED_OFFICE365_CONTACTS_LIST)
    def test_list_more_than_1000_contacts(self, _):
        result = self.list_(self.client, self.source_uuid)
        assert_that(
            result,
            has_entries(
                total=5000,
                filtered=5000,
            ),
        )
        result_items = result.get('items')
        for i in range(5000):
            expected_entry = {
                "id": f"an-id-{i}",
                "displayName": f"displayName-{i}",
                "givenName": f"givenName-{i}",
                "surname": f"surname-{i}",
                "mobilePhone": "",
                "businessPhones": ['7777777777'],
                "emailAddresses": [
                    {"address": f"email-{i}@wazoquebec.onmicrosoft.com"}
                ],
            }
            assert_that(result_items, has_item(expected_entry))

    @fixtures.office365_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.office365_source(token=VALID_TOKEN_SUB_TENANT)
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

    @fixtures.office365_result(OFFICE365_CONTACT_LIST)
    def test_list(self, office365_api):
        result = self.list_(self.client, self.source_uuid)
        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(
                    has_entries(
                        displayName='Mario Bros',
                        givenName='Mario',
                        surname='Bros',
                        emailAddresses=contains_inanyorder(
                            has_entries(address='mbros@wazoquebec.onmicrosoft.com'),
                        ),
                        mobilePhone='',
                        businessPhones=contains_inanyorder('7777777777'),
                    ),
                    has_entries(
                        id='another-id',
                        displayName='Luigi Bros',
                        givenName='Luigi',
                        surname='Bros',
                        emailAddresses=contains_inanyorder(
                            has_entries(address='lbros@wazoquebec.onmicrosoft.com'),
                        ),
                        mobilePhone='',
                        businessPhones=contains_inanyorder('5555555555'),
                    ),
                ),
                total=2,
                filtered=2,
            ),
        )

    @fixtures.office365_result(OFFICE365_CONTACT_LIST)
    def test_pagination(self, office365_api):
        mario = has_entries(displayName='Mario Bros')
        luigi = has_entries(displayName='Luigi Bros')

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

    @fixtures.office365_result(OFFICE365_CONTACT_LIST)
    def test_search(self, office365_api):
        self.list_(self.client, self.source_uuid, search='mario'),
        office365_api.verify(
            {
                'method': 'GET',
                'path': '/v1.0/me/contacts',
                'headers': {'Authorization': ['Bearer an-access-token']},
            }
        )

    def list_(self, client, *args, **kwargs):
        return client.backends.list_contacts_from_source('office365', *args, **kwargs)
