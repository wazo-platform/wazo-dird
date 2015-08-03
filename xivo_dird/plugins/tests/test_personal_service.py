# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import unittest

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import greater_than
from hamcrest import has_entry
from hamcrest import is_
from mock import Mock
from mock import patch
from mock import sentinel as s
from xivo_dird import BaseService
from xivo_dird.plugins.personal_service import PersonalServicePlugin
from xivo_dird.plugins.personal_service import _PersonalService


class TestPersonalServicePlugin(unittest.TestCase):

    def test_load_no_config(self):
        plugin = PersonalServicePlugin()

        self.assertRaises(ValueError, plugin.load, {})

    def test_that_load_returns_a_service(self):
        plugin = PersonalServicePlugin()

        service = plugin.load({'config': s.config, 'sources': {}})

        assert_that(isinstance(service, BaseService))

    @patch('xivo_dird.plugins.personal_service._PersonalService')
    def test_that_load_injects_config_and_sources_to_the_service(self, MockedPersonalService):
        plugin = PersonalServicePlugin()

        service = plugin.load({'config': s.config, 'sources': {}})

        MockedPersonalService.assert_called_once_with(s.config, {})
        assert_that(service, equal_to(MockedPersonalService.return_value))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_create_contact_calls_consul_put(self, consul_init):
        consul = consul_init.return_value
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        service.create_contact({'eyes': 'violet'}, {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.put.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_list_contacts_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), ['/my/key/', 'my/other/key/'])
        source = Mock(backend='personal')
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {'personal': source})

        service.list_contacts({'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_list_contacts_raw_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), [])
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        service.list_contacts_raw({'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_get_contact_calls_consul_get(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), [])
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        service.get_contact('contact-id', {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.get.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_edit_contact_calls_consul_put(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), [])
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        service.edit_contact('contact-id', {'firstname': 'Alice'}, {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.put.call_count, greater_than(0))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_edit_contact_does_not_accept_modifying_contact_id(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), [])
        consul.kv.put.return_value = (Mock(), [])
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        result = service.edit_contact('contact-id', {'id': 'new-id', 'firstname': 'Alice'}, {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(result, has_entry('id', 'contact-id'))

    @patch('xivo_dird.plugins.personal_service.Consul')
    def test_that_remove_contact_calls_consul_delete(self, consul_init):
        consul = consul_init.return_value
        consul.kv.get.return_value = (Mock(), [])
        service = _PersonalService({'consul': {'host': 'localhost', 'port': 8500}}, {})

        service.remove_contact('my-contact-id', {'token': 'valid-token', 'auth_id': 'my-uuid'})

        assert_that(consul.kv.delete.call_count, greater_than(0))


class TestValidateContact(unittest.TestCase):

    def test_that_validate_contact_refuses_dot_key(self):
        contact_infos = {
            '.': '.'
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_non_string_key(self):
        contact_infos = {
            1: '.'
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_non_string_value(self):
        contact_infos = {
            'a': 2
        }

        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, contact_infos)

    def test_that_validate_contact_refuses_path_related_keys(self):
        exception = _PersonalService.InvalidPersonalContact
        self.assertRaises(exception, _PersonalService.validate_contact, {'/': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'//': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'/abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abc/': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'..': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'./././abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abcd./../../../abc': '..'})
        self.assertRaises(exception, _PersonalService.validate_contact, {'abcd./../../..': '..'})

    def test_that_validate_contact_accepts_keys_with_separators(self):
        _PersonalService.validate_contact({'abcd.def.ghij': '..'})
        _PersonalService.validate_contact({'abcd/def/ghij': '..'})
        _PersonalService.validate_contact({'abcd.def/ghi.jkl': '..'})

    def test_that_validate_contact_accepts_correct_contact(self):
        contact_infos = {
            'firstname': 'Alice',
            'lastname': 'Bob',
        }

        result = _PersonalService.validate_contact(contact_infos)

        assert_that(result, is_(None))
