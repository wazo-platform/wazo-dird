# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from requests import HTTPError

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

    @contextmanager
    def profile(self, client, *args, **kwargs):
        profile = client.profiles.create(*args, **kwargs)
        try:
            yield profile
        finally:
            try:
                self.client.profiles.delete(profile['uuid'])
            except HTTPError as e:
                response = getattr(e, 'response', None)
                status_code = getattr(response, 'status_code', None)
                if status_code != 404:
                    raise


class TestDelete(BaseProfileTestCase):

    @fixtures.display()
    @fixtures.csv_source()
    def test_delete(self, source, display):
        body = {
            'name': 'profile',
            'display': display,
            'services': {'lookup': {'sources': [source]}},
        }
        with self.profile(self.client, body) as profile:
            assert_that(
                calling(self.client.profiles.delete).with_args(profile['uuid']),
                not_(raises(Exception)),
            )

            assert_that(
                calling(self.client.profiles.delete).with_args(profile['uuid']),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404)),
                ),
            )

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub_source, sub_display, main_source, main_display):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        body = {
            'name': 'profile',
            'display': main_display,
            'services': {'lookup': {'sources': [main_source]}},
        }
        with self.profile(main_tenant_client, body) as profile:
            assert_that(
                calling(sub_tenant_client.profiles.delete).with_args(profile['uuid']),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404)),
                ),
            )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        with self.profile(sub_tenant_client, body) as profile:
            assert_that(
                calling(main_tenant_client.profiles.delete).with_args(profile['uuid']),
                not_(raises(Exception)),
            )


class TestGet(BaseProfileTestCase):

    @fixtures.display()
    @fixtures.csv_source()
    def test_get(self, source, display):
        body = {
            'name': 'profile',
            'display': display,
            'services': {'lookup': {'sources': [source]}},
        }
        with self.profile(self.client, body) as profile:
            response = self.client.profiles.get(profile['uuid'])
            assert_that(response, equal_to(profile))

        assert_that(
            calling(self.client.profiles.get).with_args(UNKNOWN_UUID),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub_source, sub_display, main_source, main_display):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        body = {
            'name': 'profile',
            'display': main_display,
            'services': {'lookup': {'sources': [main_source]}},
        }
        with self.profile(main_tenant_client, body) as profile:
            assert_that(
                calling(sub_tenant_client.profiles.get).with_args(profile['uuid']),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404)),
                ),
            )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        with self.profile(sub_tenant_client, body) as profile:
            result = main_tenant_client.profiles.get(profile['uuid'])
            assert_that(result, equal_to(result))


class TestList(BaseProfileTestCase):

    @fixtures.display()
    @fixtures.csv_source()
    def test_search(self, source, display):
        base_body = {'display': display, 'services': {'lookup': {'sources': [source]}}}
        body_abc = dict(name='abc', **base_body)
        body_bcd = dict(name='bcd', **base_body)
        body_cde = dict(name='cde', **base_body)

        with self.profile(self.client, body_abc) as abc, \
                self.profile(self.client, body_bcd) as bcd, \
                self.profile(self.client, body_cde) as cde:
            result = self.client.profiles.list()
            self.assert_list_result(result, contains_inanyorder(abc, bcd, cde), total=3, filtered=3)

            result = self.client.profiles.list(name='abc')
            self.assert_list_result(result, contains(abc), total=3, filtered=1)

            result = self.client.profiles.list(uuid=cde['uuid'])
            self.assert_list_result(result, contains(cde), total=3, filtered=1)

            result = self.client.profiles.list(search='b')
            self.assert_list_result(result, contains_inanyorder(abc, bcd), total=3, filtered=2)

    @fixtures.display()
    @fixtures.csv_source()
    def test_pagination(self, source, display):
        base_body = {'display': display, 'services': {'lookup': {'sources': [source]}}}
        body_abc = dict(name='abc', **base_body)
        body_bcd = dict(name='bcd', **base_body)
        body_cde = dict(name='cde', **base_body)

        with self.profile(self.client, body_abc) as abc, \
                self.profile(self.client, body_bcd) as bcd, \
                self.profile(self.client, body_cde) as cde:
            result = self.client.profiles.list(order='name')
            self.assert_list_result(result, contains(abc, bcd, cde), total=3, filtered=3)

            result = self.client.profiles.list(order='name', direction='desc')
            self.assert_list_result(result, contains(cde, bcd, abc), total=3, filtered=3)

            result = self.client.profiles.list(order='name', limit=2)
            self.assert_list_result(result, contains(abc, bcd), total=3, filtered=3)

            result = self.client.profiles.list(order='name', offset=2)
            self.assert_list_result(result, contains(cde), total=3, filtered=3)

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub_source, main_source, sub_display, main_display):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        body_main_profile = {
            'name': 'main',
            'display': main_display,
            'services': {'lookup': {'sources': [main_source]}},
        }
        body_sub_profile = {
            'name': 'sub',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }

        with self.profile(main_tenant_client, body_main_profile) as main, \
                self.profile(sub_tenant_client, body_sub_profile) as sub:
            result = main_tenant_client.profiles.list()
            self.assert_list_result(result, contains(main), total=1, filtered=1)

            result = main_tenant_client.profiles.list(recurse=True)
            self.assert_list_result(result, contains_inanyorder(main, sub), total=2, filtered=2)

            result = sub_tenant_client.profiles.list()
            self.assert_list_result(result, contains_inanyorder(sub), total=1, filtered=1)

            result = sub_tenant_client.profiles.list(recurse=True)
            self.assert_list_result(result, contains_inanyorder(sub), total=1, filtered=1)


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
    def test_duplicate(self, source, display):
        body = {
            'name': 'profile',
            'display': display,
            'services': {'lookup': {'sources': [source]}},
        }

        with self.profile(self.client, body):
            assert_that(
                calling(self.client.profiles.create).with_args(body),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409)),
                ),
            )

    @fixtures.display()
    @fixtures.csv_source()
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    def test_unknown_display(self, unknown_display, source, display):
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

    @fixtures.display()
    @fixtures.csv_source()
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_unknown_sources(self, unknown_source, source, display):
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

        with self.profile(self.client, body) as profile:
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
        with self.profile(main_tenant_client, body, tenant_uuid=SUB_TENANT) as profile:
            assert_that(profile, has_entries(tenant_uuid=SUB_TENANT))

    def assert_invalid_body(self, body):
        try:
            self.client.profiles.create(body)
        except Exception as e:
            assert_that(e.response.status_code, equal_to(400))
            assert_that(e.response.json(), has_entries(error_id='invalid-data'))
        else:
            self.fail('Should have raised: {}'.format(body))


class TestPut(BaseProfileTestCase):

    @fixtures.display()
    @fixtures.display()
    @fixtures.csv_source()
    @fixtures.csv_source()
    def test_put(self, s2, s1, d2, d1):
        body = {
            'name': 'profile',
            'display': d1,
            'services': {'lookup': {'sources': [s1]}},
        }
        with self.profile(self.client, body) as profile:
            new_body = {
                'name': 'updated',
                'display': d2,
                'services': {
                    'reverse': {'sources': [s1, s2]},
                    'favorites': {'sources': [s2]},
                }
            }
            self.client.profiles.edit(profile['uuid'], new_body)

            assert_that(self.client.profiles.get(profile['uuid']), has_entries(
                uuid=profile['uuid'],
                name='updated',
                services=has_entries(
                    reverse=has_entries(
                        sources=contains(
                            has_entries(uuid=s1['uuid']),
                            has_entries(uuid=s2['uuid']),
                        ),
                    ),
                    favorites=has_entries(
                        sources=contains(
                            has_entries(uuid=s2['uuid']),
                        ),
                    ),
                ),
            ))

        assert_that(
            calling(self.client.profiles.edit).with_args(UNKNOWN_UUID, new_body),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    @fixtures.display()
    @fixtures.csv_source()
    def test_duplicate(self, s1, d1):
        body = {
            'display': d1,
            'services': {'lookup': {'sources': [s1]}},
        }

        with self.profile(self.client, dict(name='a', **body)), \
                self.profile(self.client, dict(name='b', **body)) as b:
            assert_that(
                calling(self.client.profiles.edit).with_args(b['uuid'], dict(name='a', **body)),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409)),
                ),
            )

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, sub_source, sub_display, main_source, main_display):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        body = {
            'name': 'profile',
            'display': main_display,
            'services': {'lookup': {'sources': [main_source]}},
        }
        with self.profile(main_tenant_client, body) as profile:
            assert_that(
                calling(sub_tenant_client.profiles.edit).with_args(profile['uuid'], body),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404)),
                ),
            )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        with self.profile(sub_tenant_client, body) as profile:
            result = main_tenant_client.profiles.edit(profile['uuid'], body)
            assert_that(result, equal_to(result))

    @fixtures.display(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.display(token=VALID_TOKEN_SUB_TENANT)
    @fixtures.csv_source()
    def test_unknown_display(self, source, sub_display, main_display):
        body = {
            'name': 'profile',
            'display': main_display,
            'services': {'lookup': {'sources': [source]}},
        }

        with self.profile(self.client, body) as profile:
            for display_uuid in [sub_display['uuid'], UNKNOWN_UUID]:
                new_body = dict(body)
                new_body['display'] = {'uuid': display_uuid}
                assert_that(
                    calling(self.client.profiles.edit).with_args(profile['uuid'], new_body),
                    raises(Exception).matching(
                        has_properties(response=has_properties(status_code=400)),
                    ),
                )

    @fixtures.display()
    @fixtures.csv_source(token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.csv_source(token=VALID_TOKEN_SUB_TENANT)
    def test_unknown_source(self, sub_source, main_source, display):
        body = {
            'name': 'profile',
            'display': display,
            'services': {'lookup': {'sources': [main_source]}},
        }

        with self.profile(self.client, body) as profile:
            for source_uuid in [sub_source['uuid'], UNKNOWN_UUID]:
                new_body = dict(body)
                new_body['services']['lookup']['sources'] = [{'uuid': source_uuid}]
                assert_that(
                    calling(self.client.profiles.edit).with_args(profile['uuid'], new_body),
                    raises(Exception).matching(
                        has_properties(response=has_properties(status_code=400)),
                    ),
                )
