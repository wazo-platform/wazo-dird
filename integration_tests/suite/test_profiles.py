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
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_
from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.fixtures import http as fixtures


class BaseProfileTestCase(BaseDirdIntegrationTest):

    asset = 'all_routes'


class TestPost(BaseProfileTestCase):

    @fixtures.display()
    def test_invalid_bodies(self, display):
        invalid_bodies = [
            {},
            {'name': None},
            {'name': 'foobar'},
            {'name': 'foobar', 'display': None},
            {'name': 'foobar', 'display': {'uuid': display['uuid']}},
        ]

        for body in invalid_bodies:
            self.assert_invalid_body(body)

    @fixtures.display()
    @fixtures.csv_source()
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_unknown_resources(self, unknown_source, unknown_display, source, display):
        for uuid in [UNKNOWN_UUID, unknown_display['uuid']]:
            unknown_display = {
                'name': 'unknown_display',
                'display': {'uuid': uuid},
                'services': {'lookup': {'sources': [source]}},
            }

            try:
                self.client.profiles.create(unknown_display)
            except Exception as e:
                assert_that(e.response.status_code, equal_to(400))
                assert_that(e.response.json(), has_entries(error_id='unknown-display'))

        for uuid in [UNKNOWN_UUID, unknown_source['uuid']]:
            unknown_source = {
                'name': 'unknown_source',
                'display': display,
                'services': {'lookup': {'sources': [{'uuid': uuid}]}},
            }

            try:
                self.client.profiles.create(unknown_source)
            except Exception as e:
                assert_that(e.response.status_code, equal_to(400))
                assert_that(e.response.json(), has_entries(error_id='unknown-source'))

    @fixtures.display()
    @fixtures.csv_source()
    def test_all_fields(self, source, display):
        body = {
            'name': 'profile',
            'display': {'uuid': display['uuid']},
            'services': {
                'lookup': {'sources': [{'uuid': source['uuid']}], 'options': {'timeout': 5}},
                'reverse': {'sources': [{'uuid': source['uuid']}], 'options': {'timeout': 0.5}},
            },
        }

        profile = self.client.profiles.create(body)

        assert_that(profile, has_entries(
            uuid=uuid_(),
            tenant_uuid=MAIN_TENANT,
            name='profile',
            display=has_entries(uuid=display['uuid']),
            services=has_entries(
                lookup=has_entries(
                    sources=contains(has_entries(uuid=source['uuid'])),
                    options=has_entries(timeout=5)
                ),
                reverse=has_entries(
                    sources=contains(has_entries(uuid=source['uuid'])),
                    options=has_entries(timeout=0.5)
                ),
            ),
        ))

    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub_display, main_display, sub_source, main_source):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        body = {
            'name': 'profile',
            'display': main_display,
            'services': {'lookup': {'sources': [main_source]}},
        }

        assert_that(
            calling(sub_tenant_client.profiles.create).with_args(body, tenant_uuid=MAIN_TENANT),
            raises(Exception).matching(has_properties(response=has_properties(status_code=401))),
        )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        profile = main_tenant_client.profiles.create(body, tenant_uuid=SUB_TENANT)
        assert_that(profile, has_entries(tenant_uuid=SUB_TENANT))
        # TODO remove the profile

    def assert_invalid_body(self, body):
        try:
            self.client.profiles.create(body)
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(e.response.json(), has_entries(error_id='invalid-data'))
        else:
            self.fail('Should have raised: {}'.format(body))
