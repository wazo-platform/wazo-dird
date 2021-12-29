# Copyright 2019-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    contains_inanyorder,
    has_entries,
    has_properties,
    not_,
)

from wazo_test_helpers.hamcrest.raises import raises
from wazo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_wazo_users_multiple_wazo_config
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)

BACKEND = 'wazo'


class TestWazoContactList(BaseDirdIntegrationTest):

    asset = 'wazo_users_multiple_wazo'
    config_factory = new_wazo_users_multiple_wazo_config

    def setUp(self):
        super().setUp()
        for source in self.client.sources.list(backend='wazo', recurse=True)['items']:
            if source['name'] == 'wazo_america':
                self.source_uuid = source['uuid']
            elif source['name'] == 'wazo_america_sub':
                self.sub_source_uuid = source['uuid']

    def test_list(self):
        result = self.contacts(self.client, self.source_uuid)
        assert_that(
            result,
            has_entries(
                total=4,
                filtered=4,
                items=contains_inanyorder(
                    has_entries(
                        id=1,
                        uuid=uuid_(),
                        firstname='John',
                        lastname='Doe',
                        exten='1234',
                        voicemail_number=None,
                        mobile_phone_number='+14184765458',
                        email='john@doe.com',
                    ),
                    has_entries(firstname='Mary'),
                    has_entries(firstname='Bob'),
                    has_entries(firstname='Charles'),
                ),
            ),
        )

        assert_that(
            result['items'][0].keys(),
            contains_inanyorder(
                'id',
                'uuid',
                'firstname',
                'lastname',
                'exten',
                'voicemail_number',
                'mobile_phone_number',
                'email',
            ),
        )

        assert_that(
            calling(self.contacts).with_args(self.client, UNKNOWN_UUID),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

    def test_multi_tenant(self):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(self.contacts).with_args(sub_tenant_client, self.source_uuid),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

        assert_that(
            calling(self.contacts).with_args(
                sub_tenant_client, self.source_uuid, tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=401))
            ),
        )

        assert_that(
            calling(self.contacts).with_args(main_tenant_client, self.sub_source_uuid),
            not_(raises(Exception)),
        )

        assert_that(
            calling(self.contacts).with_args(
                main_tenant_client, self.source_uuid, tenant_uuid=SUB_TENANT
            ),
            raises(Exception).matching(
                has_properties(response=has_properties(status_code=404))
            ),
        )

    def test_with_no_confd(self):
        self.stop_service('america')
        try:
            assert_that(
                calling(self.contacts).with_args(self.client, self.source_uuid),
                raises(Exception).matching(
                    has_properties(response=has_properties(status_code=503))
                ),
            )
        finally:
            self.start_service('america')

    def contacts(self, client, uuid, *args, **kwargs):
        return client.backends.list_contacts_from_source(
            backend=BACKEND, source_uuid=uuid, *args, **kwargs
        )
