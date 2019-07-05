# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    calling,
    has_properties,
)

from xivo_test_helpers.hamcrest.raises import raises

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_conference_config
from .helpers.constants import (
    MAIN_TENANT,
    SUB_TENANT,
    UNKNOWN_UUID,
    VALID_TOKEN_MAIN_TENANT,
    VALID_TOKEN_SUB_TENANT,
)

BACKEND = 'conference'


class TestConferenceContactList(BaseDirdIntegrationTest):

    asset = 'wazo_users_multiple_wazo'
    config_factory = new_conference_config

    def setUp(self):
        super().setUp()
        for source in self.client.sources.list(backend='conference', recurse=True)['items']:
            if source['name'] == 'confs':
                self.source_uuid = source['uuid']
            elif source['name'] == 'confs_sub':
                self.sub_source_uuid = source['uuid']

    def test_with_an_unknown_source(self):
        assert_that(
            calling(self.contacts).with_args(self.client, UNKNOWN_UUID),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    def test_multi_tenant(self):
        main_tenant_client = self.get_client(VALID_TOKEN_MAIN_TENANT)
        sub_tenant_client = self.get_client(VALID_TOKEN_SUB_TENANT)

        assert_that(
            calling(self.contacts).with_args(sub_tenant_client, self.source_uuid),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

        assert_that(
            calling(self.contacts).with_args(
                sub_tenant_client,
                self.source_uuid,
                tenant_uuid=MAIN_TENANT
            ),
            raises(Exception).matching(has_properties(response=has_properties(status_code=401))),
        )

        assert_that(
            calling(self.contacts).with_args(
                main_tenant_client,
                self.source_uuid,
                tenant_uuid=SUB_TENANT,
            ),
            raises(Exception).matching(has_properties(response=has_properties(status_code=404))),
        )

    def test_with_no_confd(self):
        self.stop_service('america')
        try:
            assert_that(
                calling(self.contacts).with_args(self.client, self.source_uuid),
                raises(Exception).matching(has_properties(
                    response=has_properties(status_code=503),
                ))
            )
        finally:
            self.start_service('america')

    def contacts(self, client, uuid, *args, **kwargs):
        return client.backends.list_contacts_from_source(
            backend=BACKEND,
            source_uuid=uuid,
            *args,
            **kwargs
        )
