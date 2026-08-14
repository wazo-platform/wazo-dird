# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import random
import string
from collections.abc import Generator
from contextlib import contextmanager
from typing import ClassVar

import requests
import yaml
from hamcrest import assert_that, equal_to, has_entries
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session
from wazo_dird_client import Client as DirdClient
from wazo_test_helpers import until
from wazo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from wazo_test_helpers.auth import AuthClient as MockAuthClient
from wazo_test_helpers.auth import MockCredentials, MockUserToken
from wazo_test_helpers.db import DBUserClient
from wazo_test_helpers.filesystem import FileSystemClient

from wazo_dird import database
from wazo_dird.database.helpers import Session, init_db

from .config import (
    Config,
    new_csv_with_multiple_displays_config,
    new_half_broken_config,
    new_null_config,
    new_personal_only_config,
)
from .constants import (
    ASSET_ROOT,
    DB_URI_FMT,
    MAIN_TENANT,
    MAIN_USER_UUID,
    SUB_TENANT,
    USER_1_UUID,
    USER_2_TOKEN,
    USER_2_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
    WAZO_UUID,
)
from .wait_strategy import RestApiOkWaitStrategy

START_TIMEOUT = int(os.getenv('INTEGRATION_TEST_TIMEOUT', '30'))
DB_ECHO = os.getenv('DB_ECHO', '').lower() in ['true', '1']


class DirdAssetRunningTestCase(AssetLaunchingTestCase):
    assets_root = ASSET_ROOT
    service = 'dird'


class DBRunningTestCase(DirdAssetRunningTestCase):
    Session: ClassVar[scoped_session]
    db_uri: ClassVar[str]
    engine: ClassVar[Engine]

    @classmethod
    def setup_db_session(cls):
        db_port = cls.service_port(5432, 'db')
        cls.db_uri = DB_URI_FMT.format(port=db_port)
        cls.engine = init_db(cls.db_uri, echo=DB_ECHO)
        cls.Session = Session

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setup_db_session()
        database.Base.metadata.reflect(bind=cls.engine)
        database.Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def clean_db(cls) -> None:
        """Empty every table without touching the schema.

        The schema of the db image comes from the alembic migrations. Dropping
        it would let `create_all` rebuild a different one from the models - the
        constraint names do not agree - so the tests would no longer run
        against the schema that we install.
        """
        # `Base.metadata` belongs to the process, and `setUpClass` reflects each
        # database into it. One session covers many assets, so the metadata
        # ends up describing tables that the current database does not have.
        existing = set(inspect(cls.engine).get_table_names())

        with cls.engine.begin() as connection:
            # DELETE takes a row lock. TRUNCATE needs an ACCESS EXCLUSIVE lock,
            # so it would queue behind the queries that dird still has in
            # flight and block the rest of the run.
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            for table in reversed(database.Base.metadata.sorted_tables):
                if table.name == 'alembic_version' or table.name not in existing:
                    continue
                connection.execute(table.delete())

        # Reclaim the dead rows and refresh the planner statistics. Without
        # this, a class that loads many contacts leaves the next one with a
        # bloated table and stale statistics, and the phonebook queries become
        # slow enough to time out.
        with cls.engine.connect().execution_options(
            isolation_level='AUTOCOMMIT'
        ) as connection:
            connection.execute(text('VACUUM (ANALYZE)'))

    @classmethod
    def analyze_db(cls) -> None:
        """Refresh the planner statistics after a bulk load.

        `clean_db` leaves the statistics of empty tables behind. A class that
        loads many rows must refresh them, otherwise the planner still believes
        the tables are empty and chooses a plan that is far too slow.
        """
        with cls.engine.connect().execution_options(
            isolation_level='AUTOCOMMIT'
        ) as connection:
            connection.execute(text('ANALYZE'))

    @classmethod
    def tearDownClass(cls):
        # A failure of the cleanup must still release the connections and stop
        # the stack, otherwise the next class of the same asset inherits the
        # leak and every later class fails too.
        try:
            cls.clean_db()
        finally:
            cls.engine.dispose()
            super().tearDownClass()

    @classmethod
    def restart_postgres(cls):
        cls.restart_service('db', signal='SIGINT')  # fast shutdown
        cls.engine.dispose()
        cls.setup_db_session()
        database = DBUserClient(cls.db_uri)
        until.true(database.is_up, timeout=5, message='Postgres did not come back up')

    @classmethod
    def restart_dird(cls):
        cls.restart_service('dird')
        cls.port = cls.service_port(9489, 'dird')
        cls.dird = cls.make_dird(VALID_TOKEN_MAIN_TENANT)

    @classmethod
    @contextmanager
    def dird_with_config(cls, config: dict) -> Generator[None, None, None]:
        filesystem = FileSystemClient(
            execute=cls.docker_exec,
            service_name='dird',
            root=True,
        )
        name = ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
        config_file = f'/etc/wazo-dird/conf.d/10-{name}.yml'
        content = yaml.dump(config)
        try:
            with filesystem.file_(config_file, content=content):
                cls.restart_dird()
                yield
        finally:
            cls.restart_dird()
            cls.wait_strategy.wait(cls.dird)


class RequestUtilMixin:
    @staticmethod
    def _update_headers(kwargs, defaults=None):
        token = kwargs.pop('token', None)
        tenant = kwargs.pop('tenant', None)
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('X-Auth-Token', token)
        kwargs['headers'].setdefault('Wazo-Tenant', tenant)
        if defaults:
            for k, v in defaults.items():
                kwargs['headers'].setdefault(k, v)
        return kwargs

    @staticmethod
    def delete(*args, **kwargs):
        kwargs = RequestUtilMixin._update_headers(kwargs)
        return requests.delete(*args, **kwargs)

    @staticmethod
    def get(*args, **kwargs):
        kwargs = RequestUtilMixin._update_headers(kwargs)
        return requests.get(*args, **kwargs)

    @staticmethod
    def post(*args, **kwargs):
        kwargs = RequestUtilMixin._update_headers(
            kwargs, defaults={'Content-Type': 'application/json'}
        )
        return requests.post(*args, **kwargs)

    @staticmethod
    def put(*args, **kwargs):
        kwargs = RequestUtilMixin._update_headers(
            kwargs, defaults={'Content-Type': 'application/json'}
        )
        return requests.put(*args, **kwargs)


class BaseDirdIntegrationTest(RequestUtilMixin, DBRunningTestCase):
    wait_strategy = RestApiOkWaitStrategy()
    config_factory = new_null_config

    host: ClassVar[str]
    port: ClassVar[int]
    mock_auth_client: ClassVar[MockAuthClient]
    dird: ClassVar[DirdClient]
    config: ClassVar[Config]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = '127.0.0.1'
        cls.port = cls.service_port(9489, 'dird')
        cls.dird = cls.make_dird(VALID_TOKEN_MAIN_TENANT)
        cls.configure_wazo_auth()
        cls.config = cls.config_factory(cls.Session)
        cls.config.setup()
        cls.wait_strategy.wait(cls.dird)

    @classmethod
    def tearDownClass(cls):
        cls.config.tear_down()
        super().tearDownClass()

    @classmethod
    def make_dird(cls, token: str) -> DirdClient:
        return DirdClient(
            '127.0.0.1',
            cls.service_port(9489, 'dird'),
            prefix=None,
            https=False,
            token=token,
        )

    @classmethod
    def make_mock_auth(cls) -> MockAuthClient:
        return MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))

    @classmethod
    def configure_wazo_auth(cls):
        cls.mock_auth_client = cls.make_mock_auth()
        credentials = MockCredentials('dird-service', 'dird-password')
        cls.mock_auth_client.set_valid_credentials(credentials, VALID_TOKEN_MAIN_TENANT)
        cls.mock_auth_client.set_token(
            MockUserToken(
                VALID_TOKEN_MAIN_TENANT,
                MAIN_USER_UUID,
                WAZO_UUID,
                {'tenant_uuid': MAIN_TENANT, 'uuid': MAIN_USER_UUID},
            )
        )
        cls.mock_auth_client.set_token(
            MockUserToken(
                VALID_TOKEN_SUB_TENANT,
                USER_1_UUID,
                WAZO_UUID,
                {'tenant_uuid': SUB_TENANT, 'uuid': USER_1_UUID},
            )
        )
        cls.mock_auth_client.set_token(
            MockUserToken(
                USER_2_TOKEN,
                USER_2_UUID,
                WAZO_UUID,
                {"tenant_uuid": SUB_TENANT, "uuid": USER_2_UUID},
            )
        )
        cls.mock_auth_client.set_tenants(
            {
                'uuid': MAIN_TENANT,
                'name': 'dird-tests-master',
                'parent_uuid': MAIN_TENANT,
            },
            {
                'uuid': SUB_TENANT,
                'name': 'dird-tests-users',
                'parent_uuid': MAIN_TENANT,
            },
        )

    @classmethod
    @contextmanager
    def auth_stopped(cls):
        cls.stop_service('auth')
        yield
        cls.start_service('auth')
        auth = cls.make_mock_auth()
        until.true(auth.is_up, timeout=START_TIMEOUT)
        cls.configure_wazo_auth()

    @classmethod
    def get_client(cls, token: str = VALID_TOKEN_MAIN_TENANT) -> DirdClient:
        return DirdClient(cls.host, cls.port, token=token, prefix=None, https=False)

    @property
    def client(self) -> DirdClient:
        return self.get_client()

    @classmethod
    def url(cls, *parts):
        return f'http://127.0.0.1:{cls.port}/0.1/{"/".join(map(str, parts))}'

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
    def lookup(cls, term, profile, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_lookup_result(term, profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_lookup_user_result(cls, term, profile, user_uuid, token=None):
        params = {'term': term}
        url = cls.url('directories', 'lookup', profile, user_uuid)
        return cls.get(url, params=params, token=token)

    @classmethod
    def lookup_user(cls, term, profile, user_uuid, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_lookup_user_result(term, profile, user_uuid, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_headers_result(cls, profile, token=None):
        url = cls.url('directories', 'lookup', profile, 'headers')
        return cls.get(url, token=token)

    @classmethod
    def headers(cls, profile):
        response = cls.get_headers_result(profile, token=VALID_TOKEN_MAIN_TENANT)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_reverse_result(cls, exten, profile, user_uuid, token=None):
        params = {'exten': exten}
        url = cls.url('directories', 'reverse', profile, user_uuid)
        return cls.get(url, params=params, token=token)

    @classmethod
    def reverse(cls, exten, profile, user_uuid, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_reverse_result(exten, profile, user_uuid, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_favorites_result(cls, profile, token=None):
        url = cls.url('directories', 'favorites', profile)
        return cls.get(url, token=token)

    @classmethod
    def favorites(cls, profile, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_favorites_result(profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        return cls.put(url, token=token)

    @classmethod
    def put_favorite(cls, directory, contact, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.put_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        return cls.delete(url, token=token)

    @classmethod
    def delete_favorite(cls, directory, contact, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.delete_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @contextmanager
    def favorite(self, source, source_entry_id, token=VALID_TOKEN_MAIN_TENANT):
        self.put_favorite(source, source_entry_id, token)
        try:
            yield
        finally:
            self.delete_favorite_result(source, source_entry_id, token)

    @classmethod
    def post_personal_result(cls, personal_infos, token=None):
        url = cls.url('personal')
        return cls.post(url, json=personal_infos, token=token)

    @classmethod
    def post_personal(cls, personal_infos, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.post_personal_result(personal_infos, token)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @contextmanager
    def personal(self, personal_infos, token=VALID_TOKEN_MAIN_TENANT):
        response = self.post_personal(personal_infos, token)
        try:
            yield response
        finally:
            self.delete_personal_result(response['id'], token)

    @classmethod
    def import_personal_result(cls, csv, token=None, encoding='utf-8'):
        url = cls.url('personal', 'import')
        content_type = f'text/csv; charset={encoding}'
        headers = {'X-Auth-Token': token, 'Content-Type': content_type}
        return cls.post(url, data=csv, headers=headers)

    @classmethod
    def import_personal(
        cls, personal_infos, token=VALID_TOKEN_MAIN_TENANT, encoding='utf-8'
    ):
        response = cls.import_personal_result(personal_infos, token, encoding)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @classmethod
    def list_personal_result(cls, token=None, **parameters):
        url = cls.url('personal')
        return cls.get(url, token=token, params=parameters)

    @classmethod
    def list_personal(cls, token=VALID_TOKEN_MAIN_TENANT, **parameters):
        response = cls.list_personal_result(token, **parameters)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def export_personal_result(cls, token=None):
        url = cls.url('personal')
        return cls.get(url, params={'format': 'text/csv'}, token=token)

    @classmethod
    def export_personal(cls, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.export_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        return cls.get(url, token=token)

    @classmethod
    def get_personal(cls, personal_id, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_personal_result(cls, personal_id, personal_infos, token=None):
        url = cls.url('personal', personal_id)
        return cls.put(url, json=personal_infos, token=token)

    @classmethod
    def put_personal(cls, personal_id, personal_infos, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.put_personal_result(personal_id, personal_infos, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def delete_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        return cls.delete(url, token=token)

    @classmethod
    def delete_personal(cls, personal_id, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.delete_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def purge_personal_result(cls, token=None):
        url = cls.url('personal')
        return cls.delete(url, token=token)

    @classmethod
    def purge_personal(cls, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.purge_personal_result(token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def get_personal_with_profile_result(cls, profile, token=None):
        url = cls.url('directories', 'personal', profile)
        return cls.get(url, token=token)

    @classmethod
    def get_personal_with_profile(cls, profile, token=VALID_TOKEN_MAIN_TENANT):
        response = cls.get_personal_with_profile_result(profile, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @staticmethod
    def assert_list_result(result, items, total, filtered):
        assert_that(result, has_entries(items=items, total=total, filtered=filtered))

    def bus_is_up(self):
        result = self.client.status.get()
        return result['bus_consumer']['status'] != 'fail'

    def _make_http_request(
        self, verb: str, endpoint: str, body: str | None, headers: dict | None = None
    ) -> requests.Response:
        port = self.service_port(9489, 'dird')
        base_url = f'http://127.0.0.1:{port}/0.1/'
        default_headers = {
            'X-Auth-Token': VALID_TOKEN_MAIN_TENANT,
        }
        req_headers = default_headers if not headers else headers

        match verb.lower():
            case 'patch':
                call = requests.patch
            case 'post':
                call = requests.post
            case 'put':
                call = requests.put
            case _:
                raise ValueError('An unexpected http verb was given')

        return call(
            base_url + endpoint,
            headers=req_headers,
            data=body,
            verify=False,
        )

    def assert_empty_body_returns_400(self, urls: list[tuple[str, str]]) -> None:
        for method, url in urls:
            response = self._make_http_request(method, url, '')
            assert response.status_code == 400, f'Error with url: ({method}) {url}'

            response = self._make_http_request(method, url, None)
            assert response.status_code == 400, f'Error with url: ({method}) {url}'


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
