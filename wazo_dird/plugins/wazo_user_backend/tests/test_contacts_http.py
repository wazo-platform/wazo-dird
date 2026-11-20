# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from typing import Any
from unittest.mock import Mock, call, patch

from flask import Flask
from hamcrest import assert_that, calling, equal_to, raises

from wazo_dird.exception import NoSuchSource

from ..http import WazoContactList

SOURCE_UUID = '3f7f5e5a-4a0d-4e0f-9d3e-0d0b0a0c0e01'
VISIBLE_TENANTS = ['tenant-1', 'tenant-2']
CONFD_USER = {
    'id': 1,
    'uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
    'line_id': 2,
    'agent_id': None,
    'firstname': 'John',
    'lastname': 'Doe',
    'email': 'john@doe.com',
    'exten': '1234',
    'mobile_phone_number': None,
    'voicemail_number': None,
    'userfield': None,
    'description': None,
    'context': 'default',
}


class TestWazoContactList(unittest.TestCase):
    def setUp(self) -> None:
        self.plugin = Mock()
        self.plugin.list_contacts.return_value = {'total': 12, 'items': [CONFD_USER]}
        self.source_service = Mock()
        self.source_service.get_plugin.return_value = self.plugin
        self.calls = Mock()
        self.calls.attach_mock(self.source_service.get, 'source')
        self.calls.attach_mock(self.plugin.list_contacts, 'list_contacts')
        patcher = patch(
            'wazo_dird.plugins.wazo_user_backend.http.get_tenant_uuids',
            return_value=VISIBLE_TENANTS,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.resource = WazoContactList(self.source_service)

    def get(self, query: str = '') -> Any:
        with Flask(__name__).test_request_context(f'/?{query}'):
            return self.resource.get(SOURCE_UUID)

    def test_the_source_is_checked_with_the_visible_tenants_before_it_is_used(
        self,
    ) -> None:
        self.get()

        assert_that(
            self.calls.mock_calls[0],
            equal_to(call.source('wazo', SOURCE_UUID, VISIBLE_TENANTS)),
        )
        assert_that(self.calls.mock_calls[1][0], equal_to('list_contacts'))
        self.source_service.get_plugin.assert_called_once_with(SOURCE_UUID)

    def test_an_unknown_source_never_reaches_the_plugin(self) -> None:
        self.source_service.get.side_effect = NoSuchSource(SOURCE_UUID)

        assert_that(calling(self.get), raises(NoSuchSource))

        self.source_service.get_plugin.assert_not_called()

    def test_the_query_string_gives_the_list_parameters(self) -> None:
        self.get('limit=5&offset=2&order=lastname&direction=desc')

        self.plugin.list_contacts.assert_called_once_with(
            search=None,
            recurse=False,
            order='lastname',
            direction='desc',
            offset=2,
            limit=5,
            order_insensitive=False,
        )

    def test_the_mobile_query_gives_the_plain_list_parameters(self) -> None:
        self.get('offset=0&order=firstname')

        self.plugin.list_contacts.assert_called_once_with(
            search=None,
            recurse=False,
            order='firstname',
            direction='asc',
            offset=0,
            limit=None,
            order_insensitive=False,
        )

    def test_the_response_keeps_its_format(self) -> None:
        result = self.get()

        assert_that(
            result,
            equal_to(
                {
                    'total': 12,
                    'filtered': 12,
                    'items': [
                        {
                            'id': 1,
                            'uuid': '7ca42f43-8bd9-4a26-acb8-cb756f42bebb',
                            'firstname': 'John',
                            'lastname': 'Doe',
                            'email': 'john@doe.com',
                            'exten': '1234',
                            'mobile_phone_number': None,
                            'voicemail_number': None,
                        }
                    ],
                }
            ),
        )
