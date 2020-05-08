# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests

from hamcrest import (
    assert_that,
    calling,
    contains,
    empty,
    equal_to,
    has_entries,
    has_properties,
    has_property,
    is_,
    not_,
)
from mock import Mock
from wazo_dird_client import Client as DirdClient
from xivo_test_helpers.auth import AuthClient as AuthMock
from xivo_test_helpers.hamcrest.raises import raises
from .base_dird_integration_test import BackendWrapper
from .helpers.base import DirdAssetRunningTestCase
from .helpers.constants import (
    SUB_TENANT,
    VALID_TOKEN_MAIN_TENANT,
)
from .helpers.fixtures import http as fixtures

requests.packages.urllib3.disable_warnings()

OFFICE365_CONTACTS = {
    "value": [
        {
            "@odata.etag": "W/\"an-odata-etag\"",
            "id": "an-id",
            "displayName": "Wario Bros",
            "givenName": "Wario",
            "surname": "Bros",
            "mobilePhone": "",
            "businessPhones": ['5555555555'],
            "emailAddresses": [
                {"address": "wbros@wazoquebec.onmicrosoft.com"},
                {},
                {},
            ],
        }
    ]
}


class BaseOffice365TestCase(DirdAssetRunningTestCase):

    service = 'dird'

    MICROSOFT_EXTERNAL_AUTH = {
        "access_token": "an-access-token",
        "scope": "a-scope",
        "token_expiration": 42,
    }

    LOOKUP_ARGS = {'user_uuid': 'a-xivo-uuid', 'token': 'a-token'}
    FAVORITE_ARGS = {'user_uuid': 'a-xivo-uuid', 'token': 'a-token'}

    WARIO = {'givenName': 'Wario', 'surname': 'Bros', 'mobilePhone': ''}

    def setUp(self):
        super().setUp()
        port = self.service_port(9489, 'dird')
        dird_config = {
            'host': 'localhost',
            'port': port,
            'token': VALID_TOKEN_MAIN_TENANT,
            'prefix': None,
            'https': False,
        }
        self.client = DirdClient(**dird_config)
        self.source = self.client.backends.create_source(
            backend=self.BACKEND, body=self.config()
        )
        self.display = self.client.displays.create(
            {'name': 'display', 'columns': [{'field': 'firstname'}]}
        )
        self.profile = self.client.profiles.create(
            {
                'name': 'default',
                'display': self.display,
                'services': {'lookup': {'sources': [self.source]}},
            }
        )
        self.auth_client_mock = AuthMock(
            host='0.0.0.0', port=self.service_port(9497, 'auth')
        )
        self.auth_client_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

    def tearDown(self):
        try:
            self.client.profiles.delete(self.profile['uuid'])
            self.client.displays.delete(self.display['uuid'])
            self.client.backends.delete_source(
                backend=self.BACKEND, source_uuid=self.source['uuid']
            )
        except requests.HTTPError:
            pass

        self.auth_client_mock.reset_external_auth()
        super().tearDown()


class BaseOffice365PluginTestCase(BaseOffice365TestCase):

    asset = 'dird_microsoft'

    def setUp(self):
        self.auth_mock = AuthMock(host='0.0.0.0', port=self.service_port(9497, 'auth'))
        self.backend = BackendWrapper(
            'office365', {'config': self.config(), 'api': Mock()}
        )

    def tearDown(self):
        self.backend.unload()
        self.auth_mock.reset_external_auth()


class TestOffice365Plugin(BaseOffice365PluginTestCase):

    asset = 'dird_microsoft'

    def config(self):
        office365_port = self.service_port(443, 'microsoft.com')
        return {
            'auth': {
                'host': 'localhost',
                'port': self.service_port(9497, 'auth'),
                'prefix': None,
                'https': False,
            },
            'endpoint': f'http://localhost:{office365_port}/v1.0/me/contacts',
            'first_matched_columns': ['businessPhones', 'mobilePhone'],
            'format_columns': {
                'number': '{businessPhones[0]}',
                'email': '{emailAddresses[0][address]}',
            },
            'name': 'office365',
            'searched_columns': ["givenName", "surname", "businessPhones"],
            'type': 'office365',
        }

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_plugin_lookup(self, office365_api):
        self.auth_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.backend.search('war', self.LOOKUP_ARGS)

        assert_that(
            result,
            contains(
                has_entries(
                    number='5555555555',
                    email='wbros@wazoquebec.onmicrosoft.com',
                    **self.WARIO,
                )
            ),
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_plugin_favorites(self, office365_api):
        self.auth_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.backend.list(['an-id'], self.FAVORITE_ARGS)

        assert_that(
            result,
            contains(
                has_entries(
                    number='5555555555',
                    email='wbros@wazoquebec.onmicrosoft.com',
                    **self.WARIO,
                )
            ),
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_plugin_reverse(self, office365_api):
        self.auth_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.backend.first('5555555555', self.LOOKUP_ARGS)

        assert_that(
            result,
            has_entries(
                number='5555555555',
                email='wbros@wazoquebec.onmicrosoft.com',
                **self.WARIO,
            ),
        )


class TestOffice365PluginWrongEndpoint(BaseOffice365PluginTestCase):

    asset = 'dird_microsoft'

    def config(self):
        return {
            'auth': {
                'host': 'localhost',
                'port': self.service_port(9497, 'auth'),
                'prefix': None,
                'https': False,
            },
            'endpoint': 'wrong-endpoint',
            'first_matched_columns': [],
            'format_columns': {
                'display_name': "{firstname} {lastname}",
                'name': "{firstname} {lastname}",
                'reverse': "{firstname} {lastname}",
                'phone_mobile': "{mobile}",
            },
            'name': 'office365',
            'searched_columns': [],
            'type': 'office365',
        }

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_plugin_lookup_with_wrong_endpoint(self, office365_api):
        self.auth_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.backend.search('war', self.LOOKUP_ARGS)

        assert_that(result, is_(empty()))


class TestDirdOffice365Plugin(BaseOffice365TestCase):

    asset = 'dird_microsoft'

    BACKEND = 'office365'
    display_body = {
        'name': 'default',
        'columns': [
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'number'},
        ],
    }

    def config(self):
        return {
            'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
            'endpoint': 'http://microsoft.com:443/v1.0/me/contacts',
            'first_matched_columns': [],
            'format_columns': {
                'firstname': "{givenName}",
                'lastname': "{surname}",
                'number': "{businessPhones[0]}",
            },
            'name': 'office365',
            'searched_columns': ["givenName", "surname", "businessPhones"],
            'type': 'office365',
        }

    def setUp(self):
        super().setUp()
        self.auth_client_mock = AuthMock(
            host='0.0.0.0', port=self.service_port(9497, 'auth')
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_microsoft_when_lookup_then_contacts_fetched(self, office365_api):
        self.auth_client_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.client.directories.lookup(term='war', profile='default')
        assert_that(
            result,
            has_entries(results=contains(has_entries(column_values=contains('Wario')))),
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_no_microsoft_when_lookup_then_no_result(self, office365_api):
        self.auth_client_mock.reset_external_auth()

        result = self.client.directories.lookup(term='war', profile='default')
        result = result['results']

        assert_that(result, is_(empty()))

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_microsoft_source_when_get_all_contacts_then_contacts_fetched(
        self, office365_api
    ):
        self.auth_client_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        result = self.client.backends.list_contacts_from_source(
            backend=self.BACKEND, source_uuid=self.source['uuid']
        )

        assert_that(
            result,
            has_entries(
                total=1,
                filtered=1,
                items=contains(
                    has_entries(
                        displayName='Wario Bros',
                        surname='Bros',
                        businessPhones=['5555555555'],
                        givenName='Wario',
                    )
                ),
            ),
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_non_existing_microsoft_source_when_get_all_contacts_then_not_found(
        self, office365_api
    ):
        self.auth_client_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        assert_that(
            calling(self.client.backends.list_contacts_from_source).with_args(
                backend=self.BACKEND, source_uuid='a-non-existing-source-uuid'
            ),
            raises(requests.HTTPError).matching(
                has_property('response', has_properties('status_code', 404))
            ),
        )

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_source_and_non_existing_tenant_when_get_all_contacts_then_not_found(
        self, office365_api
    ):
        self.auth_client_mock.set_external_auth(self.MICROSOFT_EXTERNAL_AUTH)

        assert_that(
            calling(self.client.backends.list_contacts_from_source).with_args(
                backend=self.BACKEND,
                source_uuid=self.source['uuid'],
                tenant_uuid=SUB_TENANT,
            ),
            raises(requests.HTTPError).matching(
                has_property('response', has_properties('status_code', 404))
            ),
        )


class TestDirdOffice365PluginNoEndpoint(BaseOffice365TestCase):

    asset = 'dird_microsoft'

    BACKEND = 'office365'

    def config(self):
        return {
            'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
            'first_matched_columns': [],
            'format_columns': {
                'firstname': "{givenName}",
                'lastname': "{surname}",
                'reverse': "{displayName}",
                'phone_mobile': "{mobilePhone}",
            },
            'name': 'office365',
            'searched_columns': ["givenName", "surname", "businessPhones"],
            'type': 'office365',
        }

    @fixtures.office365_result(OFFICE365_CONTACTS)
    def test_given_microsoft_when_lookup_with_no_endpoint_then_no_error(
        self, office365_api
    ):
        assert_that(
            self.source['endpoint'],
            equal_to('https://graph.microsoft.com/v1.0/me/contacts'),
        )
        assert_that(
            calling(self.client.directories.lookup).with_args(
                term='war', profile='default'
            ),
            not_(raises(Exception)),
        )


class TestDirdOffice365PluginErrorEndpoint(BaseOffice365TestCase):

    asset = 'dird_microsoft'

    BACKEND = 'office365'

    def config(self):
        return {
            'auth': {'host': 'auth', 'port': 9497, 'prefix': None, 'https': False},
            'endpoint': 'http://microsoft.com:443/v1.0/me/contacts/error',
            'first_matched_columns': [],
            'format_columns': {
                'display_name': "{firstname} {lastname}",
                'name': "{firstname} {lastname}",
                'reverse': "{firstname} {lastname}",
                'phone_mobile': "{mobile}",
            },
            'name': 'office365',
            'searched_columns': [],
            'type': 'office365',
        }

    def test_given_microsoft_when_lookup_with_error_endpoint_then_no_error(self):
        assert_that(
            calling(self.client.directories.lookup).with_args(
                term='war', profile='default'
            ),
            not_(raises(Exception)),
        )

    @fixtures.office365_error()
    def test_given_microsoft_when_fetch_all_contacts_with_error_endpoint(
        self, office365_api
    ):
        assert_that(
            calling(self.client.backends.list_contacts_from_source).with_args(
                backend=self.BACKEND, source_uuid=self.source['uuid']
            ),
            raises(requests.HTTPError).matching(
                has_property('response', has_properties('status_code', 503))
            ),
        )
