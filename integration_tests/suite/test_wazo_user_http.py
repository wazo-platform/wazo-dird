# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from uuid import uuid4
from hamcrest import (
    assert_that,
    calling,
    equal_to,
    has_entries,
    has_properties,
    not_,
)

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


class TestPost(BaseWazoCRUDTestCase):

    def test_multi_tenant(self):
        result = self.client.wazo_source.create(self.valid_body)
        assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=MAIN_TENANT))

        result = self.client.wazo_source.create(self.valid_body, tenant_uuid=SUB_TENANT)
        assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))


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
