# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from contextlib import contextmanager
from requests import HTTPError

from hamcrest import (
    assert_that,
    calling,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_properties,
    not_,
)
from xivo_test_helpers.hamcrest.raises import raises
from xivo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers.config import new_multi_source_profile
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
                    has_properties(response=has_properties(status_code=404))
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
                    has_properties(response=has_properties(status_code=404))
                ),
            )

            assert_that(
                calling(sub_tenant_client.profiles.delete).with_args(
                    profile['uuid'], tenant_uuid=MAIN_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=401))
                ),
            )

            assert_that(
                calling(main_tenant_client.profiles.delete).with_args(
                    profile['uuid'], tenant_uuid=SUB_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404))
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
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
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
                calling(sub_tenant_client.profiles.get).with_args(profile['uuid']),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404))
                ),
            )

            assert_that(
                calling(main_tenant_client.profiles.get).with_args(
                    profile['uuid'], tenant_uuid=SUB_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404))
                ),
            )

            assert_that(
                calling(sub_tenant_client.profiles.get).with_args(
                    profile['uuid'], tenant_uuid=MAIN_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=401))
                ),
            )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        with self.profile(sub_tenant_client, body) as profile:
            result = main_tenant_client.profiles.get(profile['uuid'])
            assert_that(result, equal_to(profile))


class TestList(BaseProfileTestCase):
    @fixtures.display()
    @fixtures.csv_source()
    def test_search(self, source, display):
        base_body = {'display': display, 'services': {'lookup': {'sources': [source]}}}
        body_abc = dict(name='abc', **base_body)
        body_bcd = dict(name='bcd', **base_body)
        body_cde = dict(name='cde', **base_body)

        with self.profile(self.client, body_abc) as abc, self.profile(
            self.client, body_bcd
        ) as bcd, self.profile(self.client, body_cde) as cde:
            result = self.client.profiles.list()
            self.assert_list_result(
                result, contains_inanyorder(abc, bcd, cde), total=3, filtered=3
            )

            result = self.client.profiles.list(name='abc')
            self.assert_list_result(result, contains(abc), total=3, filtered=1)

            result = self.client.profiles.list(uuid=cde['uuid'])
            self.assert_list_result(result, contains(cde), total=3, filtered=1)

            result = self.client.profiles.list(search='b')
            self.assert_list_result(
                result, contains_inanyorder(abc, bcd), total=3, filtered=2
            )

    @fixtures.display()
    @fixtures.csv_source()
    def test_pagination(self, source, display):
        base_body = {'display': display, 'services': {'lookup': {'sources': [source]}}}
        body_abc = dict(name='abc', **base_body)
        body_bcd = dict(name='bcd', **base_body)
        body_cde = dict(name='cde', **base_body)

        with self.profile(self.client, body_abc) as abc, self.profile(
            self.client, body_bcd
        ) as bcd, self.profile(self.client, body_cde) as cde:
            result = self.client.profiles.list(order='name')
            self.assert_list_result(
                result, contains(abc, bcd, cde), total=3, filtered=3
            )

            result = self.client.profiles.list(order='name', direction='desc')
            self.assert_list_result(
                result, contains(cde, bcd, abc), total=3, filtered=3
            )

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

        with self.profile(main_tenant_client, body_main_profile) as main, self.profile(
            sub_tenant_client, body_sub_profile
        ) as sub:
            result = main_tenant_client.profiles.list()
            self.assert_list_result(result, contains(main), total=1, filtered=1)

            result = main_tenant_client.profiles.list(recurse=True)
            self.assert_list_result(
                result, contains_inanyorder(main, sub), total=2, filtered=2
            )

            result = sub_tenant_client.profiles.list()
            self.assert_list_result(
                result, contains_inanyorder(sub), total=1, filtered=1
            )

            result = sub_tenant_client.profiles.list(recurse=True)
            self.assert_list_result(
                result, contains_inanyorder(sub), total=1, filtered=1
            )

            result = main_tenant_client.profiles.list(
                tenant_uuid=SUB_TENANT, recurse=True
            )
            self.assert_list_result(
                result, contains_inanyorder(sub), total=1, filtered=1
            )

            assert_that(
                calling(sub_tenant_client.profiles.list).with_args(
                    tenant_uuid=MAIN_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=401))
                ),
            )


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
                    has_properties(response=has_properties(status_code=409))
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
                'lookup': {
                    'sources': [{'uuid': source['uuid']}],
                    'options': {'timeout': 5},
                },
                'reverse': {
                    'sources': [{'uuid': source['uuid']}],
                    'options': {'timeout': 0.5},
                },
            },
        }

        with self.profile(self.client, body) as profile:
            assert_that(
                profile,
                has_entries(
                    uuid=uuid_(),
                    tenant_uuid=MAIN_TENANT,
                    name='profile',
                    display=has_entries(uuid=display['uuid']),
                    services=has_entries(
                        lookup=has_entries(
                            sources=contains(has_entries(uuid=source['uuid'])),
                            options=has_entries(timeout=5),
                        ),
                        reverse=has_entries(
                            sources=contains(has_entries(uuid=source['uuid'])),
                            options=has_entries(timeout=0.5),
                        ),
                    ),
                ),
            )

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
            calling(sub_tenant_client.profiles.create).with_args(
                body, tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=401))
            ),
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
                },
            }
            self.client.profiles.edit(profile['uuid'], new_body)

            assert_that(
                self.client.profiles.get(profile['uuid']),
                has_entries(
                    uuid=profile['uuid'],
                    name='updated',
                    services=has_entries(
                        reverse=has_entries(
                            sources=contains(
                                has_entries(uuid=s1['uuid']),
                                has_entries(uuid=s2['uuid']),
                            )
                        ),
                        favorites=has_entries(
                            sources=contains(has_entries(uuid=s2['uuid']))
                        ),
                    ),
                ),
            )

        assert_that(
            calling(self.client.profiles.edit).with_args(UNKNOWN_UUID, new_body),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

    @fixtures.display()
    @fixtures.csv_source()
    def test_duplicate(self, s1, d1):
        body = {'display': d1, 'services': {'lookup': {'sources': [s1]}}}

        with self.profile(self.client, dict(name='a', **body)), self.profile(
            self.client, dict(name='b', **body)
        ) as b:
            assert_that(
                calling(self.client.profiles.edit).with_args(
                    b['uuid'], dict(name='a', **body)
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=409))
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
                calling(sub_tenant_client.profiles.edit).with_args(
                    profile['uuid'], body
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404))
                ),
            )

            assert_that(
                calling(main_tenant_client.profiles.edit).with_args(
                    profile['uuid'], body, tenant_uuid=SUB_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=404))
                ),
            )

            assert_that(
                calling(sub_tenant_client.profiles.edit).with_args(
                    profile['uuid'], body, tenant_uuid=MAIN_TENANT
                ),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=401))
                ),
            )

        body = {
            'name': 'profile',
            'display': sub_display,
            'services': {'lookup': {'sources': [sub_source]}},
        }
        with self.profile(sub_tenant_client, body) as profile:
            main_tenant_client.profiles.edit(profile['uuid'], body)
            result = main_tenant_client.profiles.get(profile['uuid'])
            assert_that(
                result,
                has_entries(
                    uuid=profile['uuid'],
                    tenant_uuid=profile['tenant_uuid'],
                    display=has_entries(uuid=sub_display['uuid']),
                    name='profile',
                    services=has_entries(
                        lookup=has_entries(
                            sources=contains(has_entries(uuid=sub_source['uuid']))
                        )
                    ),
                ),
            )

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
                    calling(self.client.profiles.edit).with_args(
                        profile['uuid'], new_body
                    ),
                    raises(Exception).matching(
                        has_properties(response=has_properties(status_code=400))
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
                    calling(self.client.profiles.edit).with_args(
                        profile['uuid'], new_body
                    ),
                    raises(Exception).matching(
                        has_properties(response=has_properties(status_code=400))
                    ),
                )


class TestGetSourcesFromProfile(BaseProfileTestCase):

    config_factory = new_multi_source_profile

    def test_when_get_then_sources_returned(self):
        response = self.client.directories.list_sources('main')

        assert_that(
            response['items'],
            contains_inanyorder(
                has_entries(name='a_wazo_main', backend='wazo'),
                has_entries(name='personal_main', backend='personal'),
                has_entries(name='csv_main', backend='csv'),
            ),
        )

    def test_that_now_all_source_info_is_returned(self):
        response = self.client.directories.list_sources('main')

        assert_that(
            response['items'][0],
            contains_inanyorder('uuid', 'tenant_uuid', 'name', 'backend'),
        )

    def test_given_asc_direction_when_get_then_sources_returned(self):
        list_params = {'direction': 'asc'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(
                has_entries(name='a_wazo_main'),
                has_entries(name='csv_main'),
                has_entries(name='personal_main'),
            ),
        )

    def test_given_desc_direction_when_get_then_sources_returned(self):
        list_params = {'direction': 'desc'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(
                has_entries(name='personal_main', backend='personal'),
                has_entries(name='csv_main', backend='csv'),
                has_entries(name='a_wazo_main', backend='wazo'),
            ),
        )

    def test_given_random_direction_when_get_then_bad_request(self):
        list_params = {'direction': '42'}

        assert_that(
            calling(self.client.directories.list_sources).with_args(
                'main', **list_params
            ),
            raises(HTTPError).matching(
                has_properties(response=has_properties(status_code=400))
            ),
        )

    def test_given_name_order_when_get_then_sources_returned(self):
        list_params = {'order': 'name'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(
                has_entries(name='a_wazo_main', backend='wazo'),
                has_entries(name='csv_main', backend='csv'),
                has_entries(name='personal_main', backend='personal'),
            ),
        )

    def test_given_backend_order_when_get_then_sources_returned(self):
        list_params = {'order': 'backend'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(
                has_entries(name='csv_main', backend='csv'),
                has_entries(name='personal_main', backend='personal'),
                has_entries(name='a_wazo_main', backend='wazo'),
            ),
        )

    def test_given_random_order_when_get_then_bad_request(self):
        list_params = {'order': '42'}

        assert_that(
            calling(self.client.directories.list_sources).with_args(
                'main', **list_params
            ),
            raises(HTTPError).matching(
                has_properties(response=has_properties(status_code=400))
            ),
        )

    def test_given_wrong_tenant_when_get_then_not_found(self):
        assert_that(
            calling(self.client.directories.list_sources).with_args(
                'main', tenant_uuid=SUB_TENANT
            ),
            raises(HTTPError).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

        assert_that(
            calling(self.client.directories.list_sources).with_args(
                'sub', tenant_uuid=SUB_TENANT
            ),
            not_(raises(Exception)),
        )

    def test_given_sub_tenant_when_get_main_tenant_then_unauthorized(self):
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(sub_tenant_client.directories.list_sources).with_args(
                'main', tenant_uuid=MAIN_TENANT
            ),
            raises(HTTPError).matching(
                has_properties(response=has_properties(status_code=401))
            ),
        )

    def test_given_limit_when_get_then_sources_returned(self):
        list_params = {'limit': '1'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'], contains(has_entries(name='a_wazo_main', backend='wazo'))
        )

    def test_given_over_limit_when_get_then_sources_returned(self):
        list_params = {'limit': '42'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(
                has_entries(name='a_wazo_main', backend='wazo'),
                has_entries(name='csv_main', backend='csv'),
                has_entries(name='personal_main', backend='personal'),
            ),
        )

    def test_given_offset_when_get_then_sources_returned(self):
        list_params = {'offset': '2'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response['items'],
            contains(has_entries(name='personal_main', backend='personal')),
        )

    def test_given_oversized_offset_when_get_then_no_sources_returned(self):
        list_params = {'offset': '42'}

        response = self.client.directories.list_sources('main', **list_params)

        assert_that(response, has_entries(total=3, filtered=3, items=empty()))

    def test_given_order_offset_limit_when_get_then_sources_returned(self):
        list_params = {'limit': '1', 'offset': '1', 'order': 'backend'}
        response = self.client.directories.list_sources('main', **list_params)

        assert_that(
            response,
            has_entries(
                items=contains(has_entries(name='personal_main', backend='personal')),
                total=3,
                filtered=3,
            ),
        )

    def test_searches(self):
        response = self.client.directories.list_sources('main', name='personal_main')
        assert_that(
            response,
            has_entries(
                total=3,
                filtered=1,
                items=contains(has_entries(name='personal_main', backend='personal')),
            ),
        )

        response = self.client.directories.list_sources('main', backend='csv')
        assert_that(
            response,
            has_entries(
                total=3,
                filtered=1,
                items=contains(has_entries(name='csv_main', backend='csv')),
            ),
        )

        response = self.client.directories.list_sources('main', search='s')
        assert_that(
            response,
            has_entries(
                total=3,
                filtered=2,
                items=contains(
                    has_entries(name='csv_main', backend='csv'),
                    has_entries(name='personal_main', backend='personal'),
                ),
            ),
        )
