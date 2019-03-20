# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains,
    equal_to,
    has_entries,
    has_properties,
)
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from xivo_test_helpers.hamcrest.raises import raises
from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)


class BaseDisplayTestCase(BaseDirdIntegrationTest):

    asset = 'all_routes'


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

        display = self.client.displays.create(body)

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

        # TODO remove the display

    def test_multi_tenant(self):
        body = {'name': 'foo', 'columns': [{'field': 'fn'}]}

        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.displays.create).with_args(body, tenant_uuid=MAIN_TENANT),
            raises(Exception).matching(has_properties(response=has_properties(status_code=401)))
        )

        display = main_tenant_client.displays.create(body, tenant_uuid=SUB_TENANT)
        assert_that(display, has_entries(tenant_uuid=SUB_TENANT))

        # TODO remove the display

    def assert_invalid_body(self, body):
        try:
            self.client.displays.create(body)
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(e.response.json(), has_entries(error_id='invalid-data'))
        else:
            self.fail('Should have raised: {}'.format(body))
