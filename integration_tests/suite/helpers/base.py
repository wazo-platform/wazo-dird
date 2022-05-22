# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import requests
import uuid

from contextlib import contextmanager
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from hamcrest import assert_that, equal_to, has_entries

from wazo_test_helpers import until
from wazo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from wazo_test_helpers.db import DBUserClient
from wazo_test_helpers.auth import (
    AuthClient as MockAuthClient,
    MockCredentials,
    MockUserToken,
)
from wazo_dird_client import Client as DirdClient
from wazo_dird import database

from .constants import (
    ASSET_ROOT,
    DB_URI_FMT,
)
from .config import (
    new_csv_with_multiple_displays_config,
    new_half_broken_config,
    new_null_config,
    new_personal_only_config,
)
from .wait_strategy import RestApiOkWaitStrategy

WAZO_UUID = '00000000-0000-4000-8000-00003eb8004d'

MASTER_TOKEN = 'valid-token-master-tenant'
MASTER_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10'
MASTER_USER_UUID = '5f243438-a429-46a8-a992-baed872081e0'

USERS_TENANT = '00000000-0000-4000-8000-000000000202'
USER_1_UUID = '00000000-0000-4000-8000-000000000302'
USER_1_TOKEN = '00000000-0000-4000-8000-000000000102'
USER_2_UUID = '00000000-0000-4000-8000-000000000303'
USER_2_TOKEN = '00000000-0000-4000-8000-000000000103'

START_TIMEOUT = int(os.environ.get('INTEGRATION_TEST_TIMEOUT', '30'))


class DirdAssetRunningTestCase(AssetLaunchingTestCase):

    assets_root = ASSET_ROOT


class DBRunningTestCase(DirdAssetRunningTestCase):
    @classmethod
    def setup_db_session(cls):
        db_port = cls.service_port(5432, 'db')
        cls.db_uri = DB_URI_FMT.format(port=db_port)
        cls.engine = create_engine(cls.db_uri, pool_pre_ping=True)
        cls.Session = scoped_session(sessionmaker(bind=cls.engine))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_db_session()
        database.Base.metadata.bind = cls.engine
        database.Base.metadata.reflect()
        database.Base.metadata.create_all()

    @classmethod
    def tearDownClass(cls):
        try:
            database.Base.metadata.drop_all()
        except Exception:
            pass
        database.Base.metadata.bind = None
        cls.engine.dispose()
        super().tearDownClass()

    @classmethod
    def restart_postgres(cls):
        cls.restart_service('db', signal='SIGINT')  # fast shutdown
        cls.engine.dispose()
        cls.setup_db_session()
        database = DBUserClient(cls.db_uri)
        until.true(database.is_up, timeout=5, message='Postgres did not come back up')


class BaseDirdIntegrationTest(DBRunningTestCase):

    service = 'dird'
    wait_strategy = RestApiOkWaitStrategy()
    config_factory = new_null_config

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = '127.0.0.1'
        cls.port = cls.service_port(9489, 'dird')
        cls.dird = cls.make_dird(MASTER_TOKEN)
        cls.configure_wazo_auth()
        cls.config = cls.config_factory(cls.Session)
        cls.config.setup()
        cls.wait_strategy.wait(cls.dird)

    @classmethod
    def tearDownClass(cls):
        cls.config.tear_down()
        super().tearDownClass()

    @classmethod
    def make_dird(cls, token):
        return DirdClient(
            '127.0.0.1',
            cls.service_port(9489, 'dird'),
            prefix=None,
            https=False,
            token=token,
        )

    @classmethod
    def make_mock_auth(cls):
        return MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))

    @classmethod
    def configure_wazo_auth(cls):
        cls.mock_auth_client = cls.make_mock_auth()
        credentials = MockCredentials('dird-service', 'dird-password')
        cls.mock_auth_client.set_valid_credentials(credentials, MASTER_TOKEN)
        cls.mock_auth_client.set_token(
            MockUserToken(
                MASTER_TOKEN,
                MASTER_USER_UUID,
                WAZO_UUID,
                {'tenant_uuid': MASTER_TENANT, 'uuid': MASTER_USER_UUID},
            )
        )
        cls.mock_auth_client.set_token(
            MockUserToken(
                USER_1_TOKEN,
                USER_1_UUID,
                WAZO_UUID,
                {'tenant_uuid': USERS_TENANT, 'uuid': USER_1_UUID},
            )
        )
        cls.mock_auth_client.set_token(
            MockUserToken(
                USER_2_TOKEN,
                USER_2_UUID,
                WAZO_UUID,
                {"tenant_uuid": USERS_TENANT, "uuid": USER_2_UUID},
            )
        )
        cls.mock_auth_client.set_tenants(
            {
                'uuid': MASTER_TENANT,
                'name': 'dird-tests-master',
                'parent_uuid': MASTER_TENANT,
            },
            {
                'uuid': USERS_TENANT,
                'name': 'dird-tests-users',
                'parent_uuid': MASTER_TENANT,
            },
        )

    @classmethod
    def get_client(cls, token=MASTER_TOKEN):
        return DirdClient(cls.host, cls.port, token=token, prefix=None, https=False)

    @property
    def client(self):
        return self.get_client()

    @classmethod
    def url(cls, *parts):
        return 'http://127.0.0.1:{port}/0.1/{parts}'.format(
            port=cls.port, parts="/".join(map(str, parts))
        )

    @classmethod
    def get_config(cls, token):
        url = cls.url('config')
        return cls.get(url, token=token).json()

    @classmethod
    def get_lookup_result(cls, term, profile, token=None):
        params = {'term': term}
        url = cls.url('directories', 'lookup', profile)
        return cls.get(url, params=params, token=token)

    @classmethod
    def lookup(cls, term, profile, token=MASTER_TOKEN):
        response = cls.get_lookup_result(term, profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_lookup_user_result(cls, term, profile, user_uuid, token=None):
        params = {'term': term}
        url = cls.url('directories', 'lookup', profile, user_uuid)
        return cls.get(url, params=params, token=token)

    @classmethod
    def lookup_user(cls, term, profile, user_uuid, token=MASTER_TOKEN):
        response = cls.get_lookup_user_result(term, profile, user_uuid, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_headers_result(cls, profile, token=None):
        url = cls.url('directories', 'lookup', profile, 'headers')
        return cls.get(url, token=token)

    @classmethod
    def headers(cls, profile):
        response = cls.get_headers_result(profile, token=MASTER_TOKEN)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_reverse_result(cls, exten, profile, user_uuid, token=None):
        params = {'exten': exten}
        url = cls.url('directories', 'reverse', profile, user_uuid)
        return cls.get(url, params=params, token=token)

    @classmethod
    def reverse(cls, exten, profile, user_uuid, token=MASTER_TOKEN):
        response = cls.get_reverse_result(exten, profile, user_uuid, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_favorites_result(cls, profile, token=None):
        url = cls.url('directories', 'favorites', profile)
        return cls.get(url, token=token)

    @classmethod
    def favorites(cls, profile, token=MASTER_TOKEN):
        response = cls.get_favorites_result(profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        return cls.put(url, token=token)

    @classmethod
    def put_favorite(cls, directory, contact, token=MASTER_TOKEN):
        response = cls.put_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        return cls.delete(url, token=token)

    @classmethod
    def delete_favorite(cls, directory, contact, token=MASTER_TOKEN):
        response = cls.delete_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @contextmanager
    def favorite(self, source, source_entry_id, token=MASTER_TOKEN):
        self.put_favorite(source, source_entry_id, token)
        try:
            yield
        finally:
            self.delete_favorite_result(source, source_entry_id, token)

    @classmethod
    def post_phonebook(cls, tenant, phonebook_body, token=MASTER_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks')
        return cls.post(url, json=phonebook_body, token=token)

    @classmethod
    def put_phonebook(cls, tenant, phonebook_id, phonebook_body, token=MASTER_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.put(url, json=phonebook_body, token=token)

    @classmethod
    def post_phonebook_contact(
        cls, tenant, phonebook_id, contact_body, token=MASTER_TOKEN
    ):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        return cls.post(url, json=contact_body, token=token)

    @classmethod
    def import_phonebook_contact(cls, tenant, phonebook_id, body, token=MASTER_TOKEN):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', 'import'
        )
        headers = {'X-Auth-Token': token, 'Context-Type': 'text/csv; charset=utf-8'}
        return cls.post(url, data=body, headers=headers)

    @classmethod
    def put_phonebook_contact(
        cls,
        tenant,
        phonebook_id,
        contact_uuid,
        contact_body,
        token=MASTER_TOKEN,
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid
        )
        return cls.put(url, json=contact_body, token=token)

    @classmethod
    def post_personal_result(cls, personal_infos, token=None):
        url = cls.url('personal')
        return cls.post(url, json=personal_infos, token=token)

    @classmethod
    def post_personal(cls, personal_infos, token=MASTER_TOKEN):
        response = cls.post_personal_result(personal_infos, token)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @contextmanager
    def personal(self, personal_infos, token=MASTER_TOKEN):
        response = self.post_personal(personal_infos, token)
        try:
            yield response
        finally:
            self.delete_personal_result(response['id'], token)

    @classmethod
    def import_personal_result(cls, csv, token=None, encoding='utf-8'):
        url = cls.url('personal', 'import')
        content_type = 'text/csv; charset={}'.format(encoding)
        headers = {'X-Auth-Token': token, 'Content-Type': content_type}
        return cls.post(url, data=csv, headers=headers)

    @classmethod
    def import_personal(cls, personal_infos, token=MASTER_TOKEN, encoding='utf-8'):
        response = cls.import_personal_result(personal_infos, token, encoding)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @classmethod
    def list_personal_result(cls, token=None):
        url = cls.url('personal')
        return cls.get(url, token=token)

    @classmethod
    def list_personal(cls, token=MASTER_TOKEN):
        response = cls.list_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def list_phonebooks(cls, tenant, token=None, **kwargs):
        token = token or MASTER_TOKEN
        url = cls.url('tenants', tenant, 'phonebooks')
        return cls.get(url, params=kwargs, token=token)

    @classmethod
    def export_personal_result(cls, token=None):
        url = cls.url('personal')
        return cls.get(url, params={'format': 'text/csv'}, token=token)

    @classmethod
    def export_personal(cls, token=MASTER_TOKEN):
        response = cls.export_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        return cls.get(url, token=token)

    @classmethod
    def get_personal(cls, personal_id, token=MASTER_TOKEN):
        response = cls.get_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_phonebook(cls, tenant, phonebook_id, token=MASTER_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.get(url, token=token)

    @classmethod
    def get_phonebook_contact(
        cls, tenant, phonebook_id, contact_uuid, token=MASTER_TOKEN
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid
        )
        return cls.get(url, token=token)

    @classmethod
    def list_phonebook_contacts(
        cls, tenant, phonebook_id, token=MASTER_TOKEN, **kwargs
    ):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        return cls.get(url, params=kwargs, token=token)

    @classmethod
    def put_personal_result(cls, personal_id, personal_infos, token=None):
        url = cls.url('personal', personal_id)
        return cls.put(url, json=personal_infos, token=token)

    @classmethod
    def put_personal(cls, personal_id, personal_infos, token=MASTER_TOKEN):
        response = cls.put_personal_result(personal_id, personal_infos, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def delete_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        return cls.delete(url, token=token)

    @classmethod
    def delete_personal(cls, personal_id, token=MASTER_TOKEN):
        response = cls.delete_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_phonebook(cls, tenant, phonebook_id, token=MASTER_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        return cls.delete(url, token=token)

    @classmethod
    def delete_phonebook_contact(
        cls, tenant, phonebook_id, contact_id, token=MASTER_TOKEN
    ):
        url = cls.url(
            'tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_id
        )
        return cls.delete(url, token=token)

    @classmethod
    def purge_personal_result(cls, token=None):
        url = cls.url('personal')
        return cls.delete(url, token=token)

    @classmethod
    def purge_personal(cls, token=MASTER_TOKEN):
        response = cls.purge_personal_result(token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def get_personal_with_profile_result(cls, profile, token=None):
        url = cls.url('directories', 'personal', profile)
        return cls.get(url, token=token)

    @classmethod
    def get_personal_with_profile(cls, profile, token=MASTER_TOKEN):
        response = cls.get_personal_with_profile_result(profile, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @staticmethod
    def delete(*args, **kwargs):
        token = kwargs.pop('token', None)
        kwargs.setdefault('headers', {'X-Auth-Token': token})
        return requests.delete(*args, **kwargs)

    @staticmethod
    def get(*args, **kwargs):
        token = kwargs.pop('token', None)
        kwargs.setdefault('headers', {'X-Auth-Token': token})
        return requests.get(*args, **kwargs)

    @staticmethod
    def post(*args, **kwargs):
        token = kwargs.pop('token', None)
        kwargs.setdefault(
            'headers', {'X-Auth-Token': token, 'Content-Type': 'application/json'}
        )
        return requests.post(*args, **kwargs)

    @staticmethod
    def put(*args, **kwargs):
        token = kwargs.pop('token', None)
        kwargs.setdefault(
            'headers', {'X-Auth-Token': token, 'Content-Type': 'application/json'}
        )
        return requests.put(*args, **kwargs)

    @staticmethod
    def assert_list_result(result, items, total, filtered):
        assert_that(result, has_entries(items=items, total=total, filtered=filtered))

    def bus_is_up(self):
        result = self.client.status.get()
        return result['bus_consumer']['status'] != 'fail'


class BasePhonebookTestCase(BaseDirdIntegrationTest):

    asset = 'phonebook_only'

    def setUp(self):
        self.tenants = {}

    def tearDown(self):
        for tenant_name in self.tenants:
            try:
                phonebooks = self.list_phonebooks(tenant_name)['items']
            except Exception:
                continue

            for phonebook in phonebooks:
                try:
                    self.delete_phonebook(tenant_name, phonebook['id'])
                except Exception:
                    pass

    def set_tenants(self, *tenant_names):
        items = [{'uuid': MASTER_TENANT}]
        for tenant_name in tenant_names:
            self.tenants.setdefault(
                tenant_name,
                {
                    'uuid': str(uuid.uuid4()),
                    'name': tenant_name,
                    'parent_uuid': MASTER_TENANT,
                },
            )
            items.append(self.tenants[tenant_name])
        self.mock_auth_client.set_tenants(*items)


class CSVWithMultipleDisplayTestCase(BaseDirdIntegrationTest):

    asset = 'all_routes'
    config_factory = new_csv_with_multiple_displays_config


class HalfBrokenTestCase(BaseDirdIntegrationTest):

    asset = 'half_broken'
    config_factory = new_half_broken_config


class PersonalOnlyTestCase(BaseDirdIntegrationTest):

    asset = 'personal_only'
    config_factory = new_personal_only_config

    def tearDown(self):
        self.purge_personal()
        super().tearDown()
