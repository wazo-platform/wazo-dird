# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import assert_that, calling, contains, contains_inanyorder, has_properties
from wazo_test_helpers.hamcrest.raises import raises

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)
from .helpers.fixtures import http as fixtures


class TestList(BaseDirdIntegrationTest):
    asset = 'all_routes'

    @fixtures.ldap_source(name='abc')
    @fixtures.personal_source(name='bcd')
    @fixtures.csv_source(name='cde')
    def test_search(self, cde, bcd, abc):
        result = self.client.sources.list()
        self.assert_list_result(
            result,
            contains_inanyorder(
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
                self._source_to_dict('csv', **cde),
            ),
            total=3,
            filtered=3,
        )

        result = self.client.sources.list(name='abc')
        self.assert_list_result(
            result, contains(self._source_to_dict('ldap', **abc)), total=3, filtered=1
        )

        result = self.client.sources.list(backend='csv')
        self.assert_list_result(
            result, contains(self._source_to_dict('csv', **cde)), total=3, filtered=1
        )

        result = self.client.sources.list(uuid=bcd['uuid'])
        self.assert_list_result(
            result,
            contains(self._source_to_dict('personal', **bcd)),
            total=3,
            filtered=1,
        )

        result = self.client.sources.list(search='b')
        self.assert_list_result(
            result,
            contains_inanyorder(
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
            ),
            total=3,
            filtered=2,
        )

    @fixtures.ldap_source(name='abc', token=VALID_TOKEN_MAIN_TENANT)
    @fixtures.personal_source(name='bcd', token=VALID_TOKEN_SUB_TENANT)
    def test_multi_tenant(self, bcd, abc):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        result = main_tenant_client.sources.list()
        self.assert_list_result(
            result, contains(self._source_to_dict('ldap', **abc)), total=1, filtered=1
        )

        result = main_tenant_client.sources.list(recurse=True)
        self.assert_list_result(
            result,
            contains(
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
            ),
            total=2,
            filtered=2,
        )

        result = main_tenant_client.sources.list(tenant_uuid=SUB_TENANT, recurse=True)
        self.assert_list_result(
            result,
            contains(self._source_to_dict('personal', **bcd)),
            total=1,
            filtered=1,
        )

        result = sub_tenant_client.sources.list()
        self.assert_list_result(
            result,
            contains(self._source_to_dict('personal', **bcd)),
            total=1,
            filtered=1,
        )

        result = sub_tenant_client.sources.list(recurse=True)
        self.assert_list_result(
            result,
            contains(self._source_to_dict('personal', **bcd)),
            total=1,
            filtered=1,
        )

        assert_that(
            calling(sub_tenant_client.sources.list).with_args(
                tenant_uuid=MAIN_TENANT, recurse=True
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=401))
            ),
        )

    @fixtures.ldap_source(name='abc')
    @fixtures.personal_source(name='bcd')
    @fixtures.csv_source(name='cde')
    def test_pagination(self, cde, bcd, abc):
        result = self.client.sources.list(order='name')
        self.assert_list_result(
            result,
            contains(
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
                self._source_to_dict('csv', **cde),
            ),
            total=3,
            filtered=3,
        )

        result = self.client.sources.list(order='backend')
        self.assert_list_result(
            result,
            contains(
                self._source_to_dict('csv', **cde),
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
            ),
            total=3,
            filtered=3,
        )

        result = self.client.sources.list(order='name', direction='desc')
        self.assert_list_result(
            result,
            contains(
                self._source_to_dict('csv', **cde),
                self._source_to_dict('personal', **bcd),
                self._source_to_dict('ldap', **abc),
            ),
            total=3,
            filtered=3,
        )

        result = self.client.sources.list(order='name', limit=2)
        self.assert_list_result(
            result,
            contains(
                self._source_to_dict('ldap', **abc),
                self._source_to_dict('personal', **bcd),
            ),
            total=3,
            filtered=3,
        )

        result = self.client.sources.list(order='name', offset=2)
        self.assert_list_result(
            result, contains(self._source_to_dict('csv', **cde)), total=3, filtered=3
        )

    @staticmethod
    def _source_to_dict(backend, uuid, name, tenant_uuid, **ignored):
        return {
            'uuid': uuid,
            'name': name,
            'backend': backend,
            'tenant_uuid': tenant_uuid,
        }
