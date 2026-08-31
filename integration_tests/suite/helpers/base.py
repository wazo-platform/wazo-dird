# Copyright 2019-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import random
import string
import unittest
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, ClassVar

import pytest
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


use_asset = pytest.mark.usefixtures


class DirdAssetLaunchingTestCase(AssetLaunchingTestCase):
    """Owns the lifecycle of one docker asset.

    `wazo_test_helpers.pytest_asset` drives the subclasses from a session
    fixture, so one stack serves every test class that asks for the same asset.
    """

    # These classes hold a stack, they hold no test.
    __test__ = False

    assets_root = ASSET_ROOT
    service = 'dird'


# `csv_with_no_unique_column` has no class: it names data files, not a stack.


class AllRoutesAsset(DirdAssetLaunchingTestCase):
    asset = 'all_routes'


class CsvWithPipesAsset(DirdAssetLaunchingTestCase):
    asset = 'csv_with_pipes'


class CsvWsIso88591WithComaAsset(DirdAssetLaunchingTestCase):
    asset = 'csv_ws_iso88591_with_coma'


class CsvWsUtf8WithPipesWithSslAsset(DirdAssetLaunchingTestCase):
    asset = 'csv_ws_utf8_with_pipes_with_ssl'


class DatabaseAsset(DirdAssetLaunchingTestCase):
    asset = 'database'


class DirdGoogleAsset(DirdAssetLaunchingTestCase):
    asset = 'dird_google'


class DirdMicrosoftAsset(DirdAssetLaunchingTestCase):
    asset = 'dird_microsoft'


class FavoriteMigrationAsset(DirdAssetLaunchingTestCase):
    asset = 'favorite_migration'


class GraphqlLoadAsset(DirdAssetLaunchingTestCase):
    # `performance_suite/helpers` is a symlink on `suite/helpers`, so the
    # performance tests need their asset here too.
    asset = 'graphql_load'


class HalfBrokenAsset(DirdAssetLaunchingTestCase):
    asset = 'half_broken'


class LdapAsset(DirdAssetLaunchingTestCase):
    asset = 'ldap'


class LdapCityAsset(DirdAssetLaunchingTestCase):
    asset = 'ldap_city'


class LdapServiceDownAsset(DirdAssetLaunchingTestCase):
    asset = 'ldap_service_down'


class LdapServiceInnactiveAsset(DirdAssetLaunchingTestCase):
    asset = 'ldap_service_innactive'


class MultipleSourcesAsset(DirdAssetLaunchingTestCase):
    asset = 'multiple_sources'


class PersonalOnlyAsset(DirdAssetLaunchingTestCase):
    asset = 'personal_only'


class PhonebookOnlyAsset(DirdAssetLaunchingTestCase):
    asset = 'phonebook_only'


class ServiceTimeoutAsset(DirdAssetLaunchingTestCase):
    asset = 'service_timeout'


class WazoConfdAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_confd'


class WazoNoConfdAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_no_confd'


class WazoUsersLateConfdAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_users_late_confd'


class WazoUsersMissingOneWazoAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_users_missing_one_wazo'


class WazoUsersMultipleWazoAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_users_multiple_wazo'


class WazoUsersTwoWorkingOne404Asset(DirdAssetLaunchingTestCase):
    asset = 'wazo_users_two_working_one_404'


class WazoUsersTwoWorkingOneTimeoutAsset(DirdAssetLaunchingTestCase):
    asset = 'wazo_users_two_working_one_timeout'


# The name of the asset is already on each class, so read it back from there.
ASSET_CLASSES: dict[str, type[DirdAssetLaunchingTestCase]] = {
    asset_class.asset: asset_class
    for asset_class in DirdAssetLaunchingTestCase.__subclasses__()
}


class DirdAssetRunningTestCase(unittest.TestCase):
    """Base of the test classes. It does not start anything itself.

    A subclass names the stack it needs with `asset = '<name>'`. That gives it
    the matching `asset_cls` and the `usefixtures` marker that the plugin reads
    to group the classes and to start the stack once.
    """

    asset: ClassVar[str]
    asset_cls: ClassVar[type[DirdAssetLaunchingTestCase]]
    pytestmark: ClassVar[list[pytest.MarkDecorator]]
    # A few tests build a path to an asset file, so they need this too.
    assets_root = ASSET_ROOT

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # bind the shared asset class
        declared = cls.__dict__.get('asset')
        if declared is not None:
            if declared not in ASSET_CLASSES:
                raise RuntimeError(
                    f'{cls.__name__} asks for the unknown asset {declared!r}; '
                    'add a subclass of DirdAssetLaunchingTestCase for it'
                )
            cls.asset_cls = ASSET_CLASSES[declared]

        # Mark only the collected classes: pytest gathers `pytestmark` along the
        # whole MRO and the plugin keeps the first, so a marker on a base class
        # would win over the one of its subclasses.
        asset = getattr(cls, 'asset', None)
        if asset is not None and cls.__name__.startswith('Test'):
            cls.pytestmark = [use_asset(asset)]

    # The asset class owns the stack, so these reach it. They are the only
    # methods of it that the tests use; `*args` avoids a copy of its signatures.
    @classmethod
    def service_port(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.service_port(*args, **kwargs)

    @classmethod
    def docker_exec(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.docker_exec(*args, **kwargs)

    @classmethod
    def restart_service(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.restart_service(*args, **kwargs)

    @classmethod
    def stop_service(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.stop_service(*args, **kwargs)

    @classmethod
    def start_service(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.start_service(*args, **kwargs)

    @classmethod
    def capture_logs(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls.capture_logs(*args, **kwargs)

    @classmethod
    def _run_cmd(cls, *args: Any, **kwargs: Any) -> Any:
        return cls.asset_cls._run_cmd(*args, **kwargs)


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

    @classmethod
    def clean_db(cls) -> None:
        """Empty every table, keeping the schema that alembic installed."""
        # ensure a fresh current view of db tables
        existing = set(inspect(cls.engine).get_table_names())

        with cls.engine.begin() as connection:
            # use delete to take a row lock instead of an exclusive lock
            # (avoid deadlock)
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            for table in reversed(database.Base.metadata.sorted_tables):
                if table.name == 'alembic_version' or table.name not in existing:
                    continue
                connection.execute(table.delete())

        # update stats so previous data churn does not impact planning on the
        # next test run
        with cls.engine.connect().execution_options(
            isolation_level='AUTOCOMMIT'
        ) as connection:
            connection.execute(text('VACUUM (ANALYZE)'))

    @classmethod
    def analyze_db(cls) -> None:
        """Refresh the planner statistics after a bulk load."""
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
        try:
            cls.config.tear_down()
        finally:
            super().tearDownClass()

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
        try:
            yield
        finally:
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
