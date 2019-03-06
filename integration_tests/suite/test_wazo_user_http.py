# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from uuid import uuid4
from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    equal_to,
    has_entries,
    has_properties,
    not_,
)

from mock import ANY
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from xivo_test_helpers.hamcrest.raises import raises
from wazo_dird_client import Client

from .base_dird_integration_test import BaseDirdIntegrationTest
from .helpers.fixtures import http as fixtures

MAIN_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee10'
SUB_TENANT = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee11'
VALID_TOKEN_MAIN_TENANT = 'valid-token-master-tenant'
VALID_TOKEN_SUB_TENANT = 'valid-token-sub-tenant'
UNKNOWN_UUID = str(uuid4())


class BaseWazoCRUDTestCase(BaseDirdIntegrationTest):

    asset = 'all_routes'
    valid_body = {
        'name': 'internal',
        'auth': {
            'key_file': '/path/to/the/key/file',
        }
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = 'localhost'
        cls.port = cls.service_port(9489, 'dird')

    @property
    def client(self):
        return self.get_client()

    def assert_unknown_source_exception(self, source_uuid, exception):
        assert_that(exception.response.status_code, equal_to(404))
        assert_that(
            exception.response.json(),
            has_entries(
                error_id='unknown-source',
                resource='sources',
                details=has_entries(uuid=source_uuid),
            )
        )

    def get_client(self, token=VALID_TOKEN_MAIN_TENANT):
        return Client(self.host, self.port, token=token, verify_certificate=False)

    @contextmanager
    def source(self, client, *args, **kwargs):
        source = client.wazo_source.create(*args, **kwargs)
        try:
            yield source
        finally:
            self.client.wazo_source.delete(source['uuid'])


class TestDelete(BaseWazoCRUDTestCase):

    @fixtures.wazo_source(name='foobar')
    def test_delete(self, foobar):
        assert_that(
            calling(self.client.wazo_source.delete).with_args(foobar['uuid']),
            not_(raises(Exception)),
        )

        assert_that(
            calling(self.client.wazo_source.get).with_args(foobar['uuid']),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404)))
        )

        try:
            self.client.wazo_source.delete(UNKNOWN_UUID)
        except Exception as e:
            self.assert_unknown_source_exception(UNKNOWN_UUID, e)
        else:
            self.fail('Should have raised')

    @fixtures.wazo_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.wazo_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_delete_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        try:
            sub_tenant_client.wazo_source.delete(main['uuid'])
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')

        assert_that(
            calling(main_tenant_client.wazo_source.delete).with_args(sub['uuid']),
            not_(raises(Exception)),
        )


class TestList(BaseWazoCRUDTestCase):

    @fixtures.wazo_source(name='abc')
    @fixtures.wazo_source(name='bcd')
    @fixtures.wazo_source(name='cde')
    def test_searches(self, c, b, a):
        assert_that(
            self.client.wazo_source.list(),
            has_entries(
                items=contains_inanyorder(a, b, c),
                total=3,
                filtered=3,
            )
        )

        assert_that(
            self.client.wazo_source.list(name='abc'),
            has_entries(
                items=contains(a),
                total=3,
                filtered=1,
            )
        )

        assert_that(
            self.client.wazo_source.list(uuid=c['uuid']),
            has_entries(
                items=contains(c),
                total=3,
                filtered=1,
            )
        )

        result = self.client.wazo_source.list(search='b')
        assert_that(
            result,
            has_entries(
                items=contains_inanyorder(a, b),
                total=3,
                filtered=2,
            )
        )

    @fixtures.wazo_source(name='abc')
    @fixtures.wazo_source(name='bcd')
    @fixtures.wazo_source(name='cde')
    def test_pagination(self, c, b, a):
        assert_that(
            self.client.wazo_source.list(order='name'),
            has_entries(
                items=contains(a, b, c),
                total=3,
                filtered=3,
            )
        )

        assert_that(
            self.client.wazo_source.list(order='name', direction='desc'),
            has_entries(
                items=contains(c, b, a),
                total=3,
                filtered=3,
            )
        )

        assert_that(
            self.client.wazo_source.list(order='name', limit=2),
            has_entries(
                items=contains(a, b),
                total=3,
                filtered=3,
            )
        )

        assert_that(
            self.client.wazo_source.list(order='name', offset=2),
            has_entries(
                items=contains(c),
                total=3,
                filtered=3,
            )
        )

    @fixtures.wazo_source(name='abc', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.wazo_source(name='bcd', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.wazo_source(name='cde', token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, c, b, a):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            main_tenant_client.wazo_source.list(),
            has_entries(
                items=contains_inanyorder(a, b),
                total=2,
                filtered=2,
            )
        )

        assert_that(
            main_tenant_client.wazo_source.list(recurse=True),
            has_entries(
                items=contains_inanyorder(a, b, c),
                total=3,
                filtered=3,
            )
        )

        assert_that(
            sub_tenant_client.wazo_source.list(),
            has_entries(
                items=contains_inanyorder(c),
                total=1,
                filtered=1,
            )
        )

        assert_that(
            sub_tenant_client.wazo_source.list(recurse=True),
            has_entries(
                items=contains_inanyorder(c),
                total=1,
                filtered=1,
            )
        )


class TestPost(BaseWazoCRUDTestCase):

    def test_post(self):
        try:
            self.client.wazo_source.create({})
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(
                e.response.json(),
                has_entries(
                    message=ANY,
                    error_id='invalid-data',
                    details=has_entries('auth', ANY),
                ),
            )
        else:
            self.fail('Should have raised')

        with self.source(self.client, self.valid_body):
            assert_that(
                calling(self.client.wazo_source.create).with_args(self.valid_body),
                raises(Exception).matching(has_properties(response=has_properties(status_code=409)))
            )

    def test_multi_tenant(self):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        with self.source(main_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=MAIN_TENANT))

        with self.source(main_tenant_client, self.valid_body, tenant_uuid=SUB_TENANT) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        with self.source(sub_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        assert_that(
            calling(
                sub_tenant_client.wazo_source.create
            ).with_args(self.valid_body, tenant_uuid=MAIN_TENANT),
            raises(Exception).matching(has_properties(response=has_properties(status_code=401))),
        )

        with self.source(main_tenant_client, self.valid_body):
            assert_that(
                calling(sub_tenant_client.wazo_source.create).with_args(self.valid_body),
                not_(raises(Exception)),
            )


class TestPut(BaseWazoCRUDTestCase):

    def setUp(self):
        super().setUp()
        self.new_body = {
            'name': 'new',
            'auth': {'username': 'foo', 'password': 'secret'},
            'searched_columns': ['firstname'],
            'first_matched_columns': ['exten'],
            'format_columns': {
                'name': '{firstname} {lastname}',
            }
        }

    @fixtures.wazo_source(name='foobar')
    @fixtures.wazo_source(name='other')
    def test_put(self, foobar, other):
        assert_that(
            calling(self.client.wazo_source.edit).with_args(foobar['uuid'], other),
            raises(Exception).matching(has_properties(response=has_properties(status_code=409)))
        )

        assert_that(
            calling(self.client.wazo_source.edit).with_args(UNKNOWN_UUID, self.new_body),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404)))
        )

        try:
            self.client.wazo_source.edit(foobar['uuid'], {})
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(
                e.response.json(),
                has_entries(
                    message=ANY,
                    error_id='invalid-data',
                    details=has_entries('auth', ANY),
                ),
            )
        else:
            self.fail('Should have raised')

        assert_that(
            calling(self.client.wazo_source.edit).with_args(foobar['uuid'], self.new_body),
            not_(raises(Exception)),
        )

        result = self.client.wazo_source.get(foobar['uuid'])
        assert_that(
            result,
            has_entries(
                uuid=foobar['uuid'],
                tenant_uuid=foobar['tenant_uuid'],
                name='new',
                auth=has_entries(username='foo', password='secret'),
                searched_columns=['firstname'],
                first_matched_columns=['exten'],
                format_columns={'name': '{firstname} {lastname}'},
            )
        )

    @fixtures.wazo_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.wazo_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_put_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.wazo_source.edit).with_args(main['uuid'], sub),
            not_(raises(Exception).matching(
                has_properties(response=has_properties(status_code=409)))
            )
        )

        try:
            sub_tenant_client.wazo_source.edit(main['uuid'], self.new_body)
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')

        assert_that(
            calling(main_tenant_client.wazo_source.edit).with_args(sub['uuid'], self.new_body),
            not_(raises(Exception)),
        )


class TestGet(BaseWazoCRUDTestCase):

    @fixtures.wazo_source(name='foobar')
    def test_get(self, wazo):
        response = self.client.wazo_source.get(wazo['uuid'])
        assert_that(response, equal_to(wazo))

        try:
            self.client.wazo_source.get(UNKNOWN_UUID)
        except Exception as e:
            self.assert_unknown_source_exception(UNKNOWN_UUID, e)
        else:
            self.fail('Should have raised')

    @fixtures.wazo_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.wazo_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_get_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        response = main_tenant_client.wazo_source.get(sub['uuid'])
        assert_that(response, equal_to(sub))

        try:
            sub_tenant_client.wazo_source.get(main['uuid'])
        except Exception as e:
            self.assert_unknown_source_exception(main['uuid'], e)
        else:
            self.fail('Should have raised')
