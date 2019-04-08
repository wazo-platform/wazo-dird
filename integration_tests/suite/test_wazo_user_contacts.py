# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from hamcrest import (
    assert_that,
    contains_inanyorder,
    has_entries,
)

from xivo_test_helpers.hamcrest.uuid_ import uuid_

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_wazo_users_multiple_wazo_config

BACKEND = 'wazo'


class TestWazoContactList(BaseDirdIntegrationTest):

    asset = 'wazo_users_multiple_wazo'
    config_factory = new_wazo_users_multiple_wazo_config

    def setUp(self):
        super().setUp()
        for source in self.client.sources.list(backend='wazo')['items']:
            if source['name'] == 'wazo_america':
                self.source_uuid = source['uuid']
                break

    def test_list(self):
        result = self.contacts(self.client, self.source_uuid)
        assert_that(result, has_entries(
            total=4,
            filtered=4,
            items=contains_inanyorder(
                has_entries(
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
        ))

    def contacts(self, client, uuid, *args, **kwargs):
        return client.backends.list_contacts_from_source(
            backend=BACKEND,
            source_uuid=uuid,
            *args,
            **kwargs
        )
