# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
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
from unittest.mock import ANY

from wazo_test_helpers.hamcrest.uuid_ import uuid_
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.fixtures import http as fixtures

HTTP_401 = has_properties(response=has_properties(status_code=401))
HTTP_404 = has_properties(response=has_properties(status_code=404))
HTTP_409 = has_properties(response=has_properties(status_code=409))


class BaseConferenceCRUDTestCase(BaseDirdIntegrationTest):
    asset = 'all_routes'
    valid_body = {'name': 'conferences', 'auth': {'key_file': '/path/to/the/key/file'}}

    @contextmanager
    def source(self, client, *args, **kwargs):
        source = client.conference_source.create(*args, **kwargs)
        try:
            yield source
        finally:
            self.client.conference_source.delete(source['uuid'])


class TestDelete(BaseConferenceCRUDTestCase):
    @fixtures.conference_source()
    def test_delete(self, source):
        self.client.conference_source.delete(source['uuid'])
        assert_that(
            calling(self.client.conference_source.get).with_args(source['uuid']),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(self.client.conference_source.delete).with_args(UNKNOWN_UUID),
            raises(Exception).matching(HTTP_404),
        )

    @fixtures.conference_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.conference_source(token=VALID_TOKEN_SUB_TENANT)
    def test_delete_multi_tenant(self, sub, main):
        main_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_client.conference_source.delete).with_args(main['uuid']),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(sub_client.conference_source.delete).with_args(
                main['uuid'], tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(HTTP_401),
        )

        assert_that(
            calling(main_client.conference_source.delete).with_args(
                main['uuid'], tenant_uuid=SUB_TENANT
            ),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(main_client.conference_source.delete).with_args(sub['uuid']),
            not_(raises(Exception)),
        )


class TestGet(BaseConferenceCRUDTestCase):
    @fixtures.conference_source()
    def test_get(self, source):
        response = self.client.conference_source.get(source['uuid'])
        assert_that(response, equal_to(source))

        assert_that(
            calling(self.client.conference_source.get).with_args(UNKNOWN_UUID),
            raises(Exception).matching(HTTP_404),
        )

    @fixtures.conference_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.conference_source(token=VALID_TOKEN_SUB_TENANT)
    def test_get_multi_tenant(self, sub, main):
        main_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        response = main_client.conference_source.get(sub['uuid'])
        assert_that(response, equal_to(sub))

        assert_that(
            calling(main_client.conference_source.get).with_args(
                main['uuid'], tenant_uuid=SUB_TENANT
            ),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(sub_client.conference_source.get).with_args(main['uuid']),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(sub_client.conference_source.get).with_args(
                main['uuid'], tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(HTTP_401),
        )


class TestList(BaseConferenceCRUDTestCase):
    @fixtures.conference_source(name='abc')
    @fixtures.conference_source(name='bcd')
    @fixtures.conference_source(name='cde')
    def test_searches(self, c, b, a):
        assert_that(
            self.client.conference_source.list(),
            has_entries(items=contains_inanyorder(a, b, c), total=3, filtered=3),
        )

        assert_that(
            self.client.conference_source.list(name='abc'),
            has_entries(items=contains(a), total=3, filtered=1),
        )

        assert_that(
            self.client.conference_source.list(uuid=c['uuid']),
            has_entries(items=contains(c), total=3, filtered=1),
        )

        assert_that(
            self.client.conference_source.list(search='b'),
            has_entries(items=contains_inanyorder(a, b), total=3, filtered=2),
        )

    @fixtures.conference_source(name='abc')
    @fixtures.conference_source(name='bcd')
    @fixtures.conference_source(name='cde')
    def test_pagination(self, c, b, a):
        assert_that(
            self.client.conference_source.list(order='name'),
            has_entries(items=contains(a, b, c), total=3, filtered=3),
        )

        assert_that(
            self.client.conference_source.list(order='name', direction='desc'),
            has_entries(items=contains(c, b, a), total=3, filtered=3),
        )

        assert_that(
            self.client.conference_source.list(order='name', limit=2),
            has_entries(items=contains(a, b), total=3, filtered=3),
        )

        assert_that(
            self.client.conference_source.list(order='name', offset=2),
            has_entries(items=contains(c), total=3, filtered=3),
        )

    @fixtures.conference_source(name='abc', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.conference_source(name='bcd', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.conference_source(name='cde', token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, c, b, a):
        main_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            main_client.conference_source.list(),
            has_entries(items=contains_inanyorder(a, b), total=2, filtered=2),
        )

        assert_that(
            main_client.conference_source.list(recurse=True),
            has_entries(items=contains_inanyorder(a, b, c), total=3, filtered=3),
        )

        assert_that(
            main_client.conference_source.list(tenant_uuid=SUB_TENANT),
            has_entries(items=contains_inanyorder(c), total=1, filtered=1),
        )

        assert_that(
            sub_client.conference_source.list(),
            has_entries(items=contains_inanyorder(c), total=1, filtered=1),
        )

        assert_that(
            sub_client.conference_source.list(recurse=True),
            has_entries(items=contains_inanyorder(c), total=1, filtered=1),
        )

        assert_that(
            calling(sub_client.conference_source.list).with_args(
                tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(HTTP_401),
        )


class TestPost(BaseConferenceCRUDTestCase):
    def test_post(self):
        try:
            self.client.conference_source.create({})
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
                calling(self.client.conference_source.create).with_args(
                    self.valid_body
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409))
                ),
            )

    def test_multi_tenant(self):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        with self.source(main_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=MAIN_TENANT))

        with self.source(
            main_tenant_client, self.valid_body, tenant_uuid=SUB_TENANT
        ) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        with self.source(sub_tenant_client, self.valid_body) as result:
            assert_that(result, has_entries(uuid=uuid_(), tenant_uuid=SUB_TENANT))

        assert_that(
            calling(sub_tenant_client.conference_source.create).with_args(
                self.valid_body, tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=401))
            ),
        )

        with self.source(main_tenant_client, self.valid_body):
            assert_that(
                calling(sub_tenant_client.conference_source.create).with_args(
                    self.valid_body
                ),
                not_(raises(Exception)),
            )


class TestPut(BaseConferenceCRUDTestCase):
    def setUp(self):
        super().setUp()
        self.new_body = {
            'name': 'new',
            'auth': {'username': 'foo', 'password': 'secret'},
            'searched_columns': ['firstname'],
            'first_matched_columns': ['exten'],
            'format_columns': {'name': '{firstname} {lastname}'},
        }

    @fixtures.conference_source(name='foobar')
    @fixtures.conference_source(name='other')
    def test_put(self, foobar, other):
        assert_that(
            calling(self.client.conference_source.edit).with_args(
                foobar['uuid'], other
            ),
            raises(Exception).matching(HTTP_409),
        )

        assert_that(
            calling(self.client.conference_source.edit).with_args(
                UNKNOWN_UUID, self.new_body
            ),
            raises(Exception).matching(HTTP_404),
        )

        try:
            self.client.conference_source.edit(foobar['uuid'], {})
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
            calling(self.client.conference_source.edit).with_args(
                foobar['uuid'], self.new_body
            ),
            not_(raises(Exception)),
        )

        result = self.client.conference_source.get(foobar['uuid'])
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
            ),
        )

    @fixtures.conference_source(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.conference_source(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_put_multi_tenant(self, sub, main):
        main_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_client.conference_source.edit).with_args(main['uuid'], sub),
            not_(raises(Exception).matching(HTTP_409)),
        )

        assert_that(
            calling(sub_client.conference_source.edit).with_args(
                main['uuid'], self.new_body
            ),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(sub_client.conference_source.edit).with_args(
                main['uuid'], self.new_body, tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(HTTP_401),
        )

        assert_that(
            calling(main_client.conference_source.edit).with_args(
                main['uuid'], self.new_body, tenant_uuid=SUB_TENANT
            ),
            raises(Exception).matching(HTTP_404),
        )

        assert_that(
            calling(main_client.conference_source.edit).with_args(
                sub['uuid'], self.new_body
            ),
            not_(raises(Exception)),
        )
