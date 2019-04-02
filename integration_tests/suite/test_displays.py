# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import requests
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
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from xivo_test_helpers.hamcrest.raises import raises
from .helpers.base import BaseDirdIntegrationTest
from .helpers.fixtures import http as fixtures
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)


class BaseDisplayTestCase(BaseDirdIntegrationTest):

    asset = 'all_routes'


class TestDelete(BaseDisplayTestCase):

    @fixtures.display()
    def test_delete(self, display):
        assert_that(
            calling(self.client.displays.delete).with_args(display['uuid']),
            not_(raises(Exception)),
        )

        assert_that(
            calling(self.client.displays.delete).with_args(display['uuid']),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.displays.delete).with_args(main['uuid']),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

        assert_that(
            calling(main_tenant_client.displays.delete).with_args(sub['uuid']),
            not_(raises(Exception)),
        )


class TestGet(BaseDisplayTestCase):

    @fixtures.display()
    def test_get(self, display):
        response = self.client.displays.get(display['uuid'])
        assert_that(response, equal_to(display))

        assert_that(
            calling(self.client.displays.delete).with_args(UNKNOWN_UUID),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        response = main_tenant_client.displays.get(sub['uuid'])
        assert_that(response, equal_to(sub))

        assert_that(
            calling(sub_tenant_client.displays.get).with_args(main['uuid']),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )


class TestList(BaseDisplayTestCase):

    @fixtures.display(name='abc')
    @fixtures.display(name='bcd')
    @fixtures.display(name='cde')
    def test_search(self, c, b, a):
        result = self.client.displays.list()
        self.assert_list_result(result, contains_inanyorder(a, b, c), total=3, filtered=3)

        result = self.client.displays.list(name='abc')
        self.assert_list_result(result, contains(a), total=3, filtered=1)

        result = self.client.displays.list(uuid=c['uuid'])
        self.assert_list_result(result, contains(c), total=3, filtered=1)

        result = self.client.displays.list(search='b')
        self.assert_list_result(result, contains_inanyorder(a, b), total=3, filtered=2)

    @fixtures.display(name='abc', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(name='bcd', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(name='cde', token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, c, b, a):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        result = main_tenant_client.displays.list()
        self.assert_list_result(result, contains_inanyorder(a, b), total=2, filtered=2)

        result = main_tenant_client.displays.list(recurse=True)
        self.assert_list_result(result, contains_inanyorder(a, b, c), total=3, filtered=3)

        result = sub_tenant_client.displays.list()
        self.assert_list_result(result, contains(c), total=1, filtered=1)

        result = sub_tenant_client.displays.list(recurse=True)
        self.assert_list_result(result, contains(c), total=1, filtered=1)

    @fixtures.display(name='abc')
    @fixtures.display(name='bcd')
    @fixtures.display(name='cde')
    def test_pagination(self, c, b, a):
        result = self.client.displays.list(order='name')
        self.assert_list_result(result, contains(a, b, c), total=3, filtered=3)

        result = self.client.displays.list(order='name', direction='desc')
        self.assert_list_result(result, contains(c, b, a), total=3, filtered=3)

        result = self.client.displays.list(order='name', limit=2)
        self.assert_list_result(result, contains(a, b), total=3, filtered=3)

        result = self.client.displays.list(order='name', offset=2)
        self.assert_list_result(result, contains(c), total=3, filtered=3)

    @staticmethod
    def assert_list_result(result, items, total, filtered):
        assert_that(result, has_entries(
            items=items,
            total=total,
            filtered=filtered,
        ))


class TestPost(BaseDisplayTestCase):

    def test_invalid_bodies(self):
        invalid_bodies = [
            {},
            {'name': None},
            {'name': 'foobar'},
            {'name': 'foobar', 'columns': []},
            {'name': 'foobar', 'columns': [{}]},
        ]

        for body in invalid_bodies:
            self.assert_invalid_body(body)

    def test_valid_post(self):
        body = {
            'name': 'display',
            'columns': [
                {
                    'field': 'fn',
                    'title': 'Firstname',
                    'default': '',
                },
                {
                    'field': 'mobile',
                    'title': 'Mobile',
                    'type': 'number',
                    'number_display': '{firstname} (Mobile)',
                    'default': None,
                },
            ],
        }

        with self.create(self.client, body) as display:
            assert_that(display, has_entries(
                uuid=uuid_(),
                tenant_uuid=MAIN_TENANT,
                columns=contains(
                    has_entries(
                        field='fn',
                        title='Firstname',
                        default='',
                        type=None,
                        number_display=None,
                    ),
                    has_entries(
                        field='mobile',
                        title='Mobile',
                        type='number',
                        number_display='{firstname} (Mobile)',
                        default=None,
                    ),
                ),
            ))

    def test_multi_tenant(self):
        body = {'name': 'foo', 'columns': [{'field': 'fn'}]}

        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.displays.create).with_args(body, tenant_uuid=MAIN_TENANT),
            raises(Exception).matching(has_properties(response=has_properties(status_code=401)))
        )

        with self.create(main_tenant_client, body, tenant_uuid=SUB_TENANT) as display:
            assert_that(display, has_entries(tenant_uuid=SUB_TENANT))

    def assert_invalid_body(self, body):
        try:
            self.client.displays.create(body)
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(e.response.json(), has_entries(error_id='invalid-data'))
        else:
            self.fail('Should have raised: {}'.format(body))

    @contextmanager
    def create(self, client, *args, **kwargs):
        display = client.displays.create(*args, **kwargs)
        try:
            yield display
        finally:
            try:
                self.client.displays.delete(display['uuid'])
            except requests.HTTPError as e:
                response = getattr(e, 'response', None)
                status_code = getattr(response, 'status_code', None)
                if status_code != 404:
                    raise


class TestPut(BaseDisplayTestCase):

    def setUp(self):
        super().setUp()
        self.valid_body = {
            'name': 'display',
            'columns': [
                {
                    'field': 'fn',
                    'title': 'Firstname',
                    'default': '',
                },
                {
                    'field': 'mobile',
                    'title': 'Mobile',
                    'type': 'number',
                    'number_display': '{firstname} (Mobile)',
                    'default': None,
                },
            ],
        }

    @fixtures.display()
    def test_put(self, display):
        self.client.displays.edit(display['uuid'], self.valid_body)

        result = self.client.displays.get(display['uuid'])
        assert_that(result, has_entries(
            uuid=display['uuid'],
            tenant_uuid=display['tenant_uuid'],
            name=self.valid_body['name'],
            columns=contains(
                has_entries(self.valid_body['columns'][0]),
                has_entries(self.valid_body['columns'][1]),
            ),
        ))

        assert_that(
            calling(self.client.displays.edit).with_args(UNKNOWN_UUID, self.valid_body),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    @fixtures.display()
    def test_invalid_bodies(self, display):
        invalid_bodies = [
            {},
            {'name': None},
            {'name': 'foobar'},
            {'name': 'foobar', 'columns': []},
            {'name': 'foobar', 'columns': [{}]},
        ]

        for body in invalid_bodies:
            self.assert_invalid_body(display['uuid'], body)

    def assert_invalid_body(self, display_uuid, body):
        try:
            self.client.displays.edit(display_uuid, body)
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(e.response.json(), has_entries(error_id='invalid-data'))
        else:
            self.fail('Should have raised: {}'.format(body))

    @fixtures.display(name='foomain', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(name='foosub', token=VALID_TOKEN_SUB_TENANT)
    def test_put_multi_tenant(self, sub, main):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(main_tenant_client.displays.edit).with_args(main['uuid'], sub),
            not_(raises(Exception)),
            'failed to create a duplicate in different tenants',
        )

        assert_that(
            calling(sub_tenant_client.displays.edit).with_args(main['uuid'], self.valid_body),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

        assert_that(
            calling(main_tenant_client.displays.edit).with_args(sub['uuid'], self.valid_body),
            not_(raises(Exception)),
        )
