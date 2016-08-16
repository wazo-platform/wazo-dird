# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Avencall
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

from hamcrest import assert_that, equal_to
from mock import ANY, Mock, sentinel as s, patch

from ..phonebook_view import ContactAll, PhonebookAll, PhonebookOne

from xivo_dird.core.exception import InvalidContactException, InvalidPhonebookException
from xivo_dird.database import DuplicatedContactException, DuplicatedPhonebookException, NoSuchPhonebook
from xivo_dird.plugins.phonebook_service import _PhonebookService as PhonebookService


class TestContactAll(unittest.TestCase):

    def setUp(self):
        self.service = Mock(PhonebookService)
        self.view = ContactAll()
        self.view.configure(self.service)
        self.body = {'firstname': 'Foo',
                     'lastname': 'Bar',
                     'number': '5551231111'}

    def test_a_workong_post(self):
        result = self._post(s.tenant, s.phonebook_id, self.body)

        self.service.create_contact.assert_called_once_with(s.tenant, s.phonebook_id, self.body)
        expected = self.service.create_contact.return_value, 201
        assert_that(result, equal_to(expected))

    def test_creating_a_contact_in_an_unknown_phonebook(self):
        self.service.create_contact.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self._post(s.tenant, s.phonebook_id, self.body)

        self.service.create_contact.assert_called_once_with(s.tenant, s.phonebook_id, self.body)
        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def test_creating_a_duplicate_contact(self):
        self.service.create_contact.side_effect = DuplicatedContactException

        result = self._post(s.tenant, s.phonebook_id, self.body)

        self.service.create_contact.assert_called_once_with(s.tenant, s.phonebook_id, self.body)
        self._assert_error(result, 409, 'Duplicating contact')

    def test_creating_an_invalid_contact(self):
        self.service.create_contact.side_effect = InvalidContactException('invalid')

        result = self._post(s.tenant, s.phonebook_id, {})

        self._assert_error(result, 400, 'invalid')

    def test_a_working_get(self):
        self.service.list_contact.return_value = [s.contact_1, s.contact_2, s.contact_3]
        self.service.count_contact.return_value = 3

        result = self._get(s.tenant, s.phonebook_id)

        assert_that(result, equal_to(({'total': 3,
                                       'items': [s.contact_1, s.contact_2, s.contact_3]}, 200)))

    def test_get_with_all_arguments(self):
        contacts = self.service.list_contact.return_value = [s.contact_1]
        total = self.service.count_contact.return_value = 3

        result = self._get(s.tenant, s.phonebook_id, search=s.search,
                           limit=s.limit, offset=s.offset, order=s.order, direction=s.direction)

        assert_that(result, equal_to(({'total': total, 'items': contacts}, 200)))
        self.service.count_contact.assert_called_once_with(s.tenant, s.phonebook_id, search=s.search)
        self.service.list_contact.assert_called_once_with(s.tenant, s.phonebook_id, search=s.search,
                                                          limit=s.limit, offset=s.offset,
                                                          order=s.order, direction=s.direction)

    def test_get_with_an_unknown_phonebook(self):
        self.service.count_contact.side_effect = NoSuchPhonebook(s.phonebook_id)
        self.service.list_contact.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self._get(s.tenant, s.phonebook_id)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def _assert_error(self, result, status_code, msg):
        error = {'reason': [msg],
                 'timestamp': [ANY],
                 'status_code': status_code}
        assert_that(result, equal_to((error, status_code)))
        result = self._post(s.tenant, s.phonebook_id, s.body)

    def _get(self, tenant, phonebook_id,
             limit=None, offset=None,
             order=None, direction=None,
             search=None):
        args = {}
        if limit:
            args['limit'] = limit
        if offset:
            args['offset'] = offset
        if order:
            args['order'] = order
        if direction:
            args['direction'] = direction
        if search:
            args['search'] = search

        with patch('xivo_dird.plugins.phonebook_view.request', Mock(args=args)):
            return self.view.get(tenant, phonebook_id)

    def _post(self, tenant, phonebook_id, body):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(json=body, args={})):
            return self.view.post(tenant, phonebook_id)


class TestPhonebookAll(unittest.TestCase):

    def setUp(self):
        self.service = Mock(PhonebookService)
        self.view = PhonebookAll()
        self.view.configure(self.service)

    def test_a_working_post(self):
        body = {'name': 'foo', 'description': 'bar'}

        result = self._post('tenant', body)

        self.service.create_phonebook.assert_called_once_with('tenant', body)
        expected = self.service.create_phonebook.return_value, 201
        assert_that(result, equal_to(expected))

    def test_that_an_invalid_body_returns_a_400(self):
        self.service.create_phonebook.side_effect = InvalidPhonebookException(s.error)

        result = self._post('tenant', {'name': 'name'})

        expected = ({'reason': [s.error], 'timestamp': [ANY], 'status_code': 400}, 400)
        assert_that(result, equal_to(expected))

    def test_that_duplicated_phonebooks_return_409(self):
        self.service.create_phonebook.side_effect = DuplicatedPhonebookException

        response = self._post('tenant', {'name': 'duplicate'})

        expected = ({'reason': ['Adding this phonebook would create a duplicate'],
                     'timestamp': [ANY],
                     'status_code': 409}, 409)
        assert_that(response, equal_to(expected))

    def test_a_working_get(self):
        self.service.list_phonebook.return_value = phonebooks = [s.phonebook_1, s.phonebook_2, s.phonebook_3]
        self.service.count_phonebook.return_value = count = len(phonebooks)

        result = self._get('tenant')

        expected = {'items': phonebooks,
                    'total': count}
        assert_that(result, equal_to(expected))
        self.service.list_phonebook.assert_called_once_with('tenant')

    def test_a_working_get_with_a_limit(self):
        limit = 2
        offset = 1
        self.service.count_phonebook.return_value = count = 42
        self.service.list_phonebook.return_value = phonebooks = [s.phonebook_2, s.phonebook_3]

        result = self._get('tenant', limit=limit, offset=1)

        expected = {'items': phonebooks,
                    'total': count}
        assert_that(result, equal_to(expected))
        self.service.list_phonebook.assert_called_once_with('tenant', limit=limit, offset=offset)
        self.service.count_phonebook.assert_called_once_with('tenant')

    def test_a_working_get_with_sorting(self):
        self.service.list_phonebook.return_value = phonebooks = [s.phonebook_1, s.phonebook_2, s.phonebook_3]
        self.service.count_phonebook.return_value = count = len(phonebooks)

        result = self._get('tenant', order='name', direction='asc')

        expected = {'items': phonebooks,
                    'total': count}
        assert_that(result, equal_to(expected))
        self.service.list_phonebook.assert_called_once_with('tenant', order='name', direction='asc')
        self.service.count_phonebook.assert_called_once_with('tenant')

    def test_a_working_get_with_a_search_param(self):
        self.service.list_phonebook.return_value = phonebooks = [s.phonebook_1, s.phonebook_2, s.phonebook_3]
        self.service.count_phonebook.return_value = count = len(phonebooks)

        result = self._get('tenant', search='foobar')

        expected = {'items': phonebooks,
                    'total': count}
        assert_that(result, equal_to(expected))
        self.service.list_phonebook.assert_called_once_with('tenant', search='foobar')
        self.service.count_phonebook.assert_called_once_with('tenant', search='foobar')

    def _get(self, tenant, limit=None, offset=None, order=None, direction=None, search=None):
        args = {}
        if limit:
            args['limit'] = limit
        if offset:
            args['offset'] = offset
        if order:
            args['order'] = order
        if direction:
            args['direction'] = direction
        if search:
            args['search'] = search

        with patch('xivo_dird.plugins.phonebook_view.request', Mock(args=args)):
            return self.view.get(tenant)

    def _post(self, tenant, body):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(json=body, args={})):
            return self.view.post(tenant)


class TestPhonebookOne(unittest.TestCase):

    def setUp(self):
        self.service = Mock(PhonebookService)
        self.view = PhonebookOne()
        self.view.configure(self.service)

    def test_a_working_get(self):
        result = self.view.get(s.tenant, s.phonebook_id)

        assert_that(result, equal_to((self.service.get_phonebook.return_value, 200)))
        self.service.get_phonebook.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_get_with_an_unknown_id(self):
        phonebook_id = 42
        self.service.get_phonebook.side_effect = NoSuchPhonebook(phonebook_id)

        result = self.view.get(s.tenant, phonebook_id)

        assert_that(result, equal_to(({'reason': ['No such phonebook: {}'.format(phonebook_id)],
                                       'timestamp': [ANY],
                                       'status_code': 404}, 404)))
        self.service.get_phonebook.assert_called_once_with(s.tenant, phonebook_id)

    def test_a_working_delete(self):
        result = self.view.delete(s.tenant, s.phonebook_id)

        assert_that(result, equal_to(('', 204)))
        self.service.delete_phonebook.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_delete_with_an_unknown_id(self):
        phonebook_id = 1
        self.service.delete_phonebook.side_effect = NoSuchPhonebook(phonebook_id)

        result = self.view.delete(s.tenant, phonebook_id)

        assert_that(result, equal_to(({'reason': ['No such phonebook: {}'.format(phonebook_id)],
                                       'timestamp': [ANY],
                                       'status_code': 404}, 404)))
        self.service.delete_phonebook.assert_called_once_with(s.tenant, phonebook_id)

    def test_a_working_put(self):
        result = self._put(s.tenant, s.phonebook_id, s.body)

        assert_that(result, equal_to((self.service.edit_phonebook.return_value, 200)))
        self.service.edit_phonebook.assert_called_once_with(s.tenant, s.phonebook_id, s.body)

    def test_put_with_an_unknown_id(self):
        self.service.edit_phonebook.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self._put(s.tenant, s.phonebook_id, s.body)

        assert_that(result, equal_to(({'reason': ['No such phonebook: {}'.format(s.phonebook_id)],
                                       'timestamp': [ANY],
                                       'status_code': 404}, 404)))
        self.service.edit_phonebook.assert_called_once_with(s.tenant, s.phonebook_id, s.body)

    def test_put_with_an_invalid_body(self):
        self.service.edit_phonebook.side_effect = InvalidPhonebookException(s.error)

        result = self._put(s.tenant, s.phonebook_id, s.body)

        assert_that(result, equal_to(({'reason': [s.error],
                                       'timestamp': [ANY],
                                       'status_code': 400}, 400)))
        self.service.edit_phonebook.assert_called_once_with(s.tenant, s.phonebook_id, s.body)

    def test_a_put_that_would_create_a_duplicate(self):
        self.service.edit_phonebook.side_effect = DuplicatedPhonebookException

        result = self._put(s.tenant, s.phonebook_id, s.body)

        assert_that(result, equal_to(({'reason': [ANY],
                                       'timestamp': [ANY],
                                       'status_code': 409}, 409)))
        self.service.edit_phonebook.assert_called_once_with(s.tenant, s.phonebook_id, s.body)

    def _put(self, tenant, phonebook_id, body):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(json=body, args={})):
            return self.view.put(tenant, phonebook_id)
