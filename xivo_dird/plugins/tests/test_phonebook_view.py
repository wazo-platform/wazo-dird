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

from hamcrest import (assert_that,
                      calling,
                      contains_inanyorder,
                      empty,
                      equal_to,
                      has_entries,
                      raises)
from mock import ANY, Mock, patch, sentinel as s

from ..phonebook_view import (_ArgParser as ArgParser,
                              ContactAll,
                              ContactImport,
                              ContactOne,
                              PhonebookAll,
                              PhonebookOne)

from xivo_dird.core.exception import (DatabaseServiceUnavailable,
                                      DuplicatedContactException,
                                      DuplicatedPhonebookException,
                                      InvalidArgumentError,
                                      InvalidContactException,
                                      InvalidPhonebookException,
                                      NoSuchContact,
                                      NoSuchPhonebook)
from xivo_dird.plugins.phonebook_service import _PhonebookService as PhonebookService


class _HTTPErrorChecker(object):

    def _assert_error(self, result, status_code, msg):
        error = {'reason': [msg],
                 'timestamp': [ANY],
                 'status_code': status_code}
        assert_that(result, equal_to((error, status_code)))


class _PhonebookViewTest(unittest.TestCase):

    def setUp(self):
        self.service = Mock(PhonebookService)
        self.view = self._View()
        self.view.configure(self.service)


class TestContactAll(_PhonebookViewTest, _HTTPErrorChecker):

    _View = ContactAll

    def setUp(self):
        super(TestContactAll, self).setUp()
        self.body = {'firstname': 'Foo',
                     'lastname': 'Bar',
                     'number': '5551231111'}

    def test_a_working_post(self):
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
        offset, limit, direction = 5, 3, 'asc'

        result = self._get(s.tenant, s.phonebook_id, search=s.search,
                           limit=limit, offset=offset, order=s.order, direction=direction)

        assert_that(result, equal_to(({'total': total, 'items': contacts}, 200)))
        self.service.count_contact.assert_called_once_with(s.tenant, s.phonebook_id, search=s.search)
        self.service.list_contact.assert_called_once_with(s.tenant, s.phonebook_id, search=s.search,
                                                          limit=limit, offset=offset,
                                                          order=s.order, direction=direction)

    def test_get_with_an_unknown_phonebook(self):
        self.service.count_contact.side_effect = NoSuchPhonebook(s.phonebook_id)
        self.service.list_contact.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self._get(s.tenant, s.phonebook_id)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def test_when_postgresql_is_down(self):
        self.service.count_contact.side_effect = DatabaseServiceUnavailable()

        result = self._get(s.tenant, s.phonebook_id)

        self._assert_error(result, 503, str(DatabaseServiceUnavailable()))

    def test_get_with_invalid_params(self):
        result = self._get(s.tenant, s.phonebook_id, offset='foobar')

        self._assert_error(result, 400, 'offset should be a positive integer')

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


class TestPhonebookAll(_PhonebookViewTest, _HTTPErrorChecker):

    _View = PhonebookAll

    def test_a_working_post(self):
        body = {'name': 'foo', 'description': 'bar'}

        result = self._post('tenant', body)

        self.service.create_phonebook.assert_called_once_with('tenant', body)
        expected = self.service.create_phonebook.return_value, 201
        assert_that(result, equal_to(expected))

    def test_that_an_invalid_body_returns_a_400(self):
        self.service.create_phonebook.side_effect = InvalidPhonebookException(s.error)

        result = self._post('tenant', {'name': 'name'})

        self._assert_error(result, 400, str(s.error))

    def test_that_duplicated_phonebooks_return_409(self):
        self.service.create_phonebook.side_effect = DuplicatedPhonebookException

        result = self._post('tenant', {'name': 'duplicate'})

        self._assert_error(result, 409, 'Duplicating phonebook')

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

    def test_get_with_invalid_params(self):
        result = self._get('tenant', offset='foobar')

        self._assert_error(result, 400, 'offset should be a positive integer')

    def test_when_postgresql_is_down(self):
        self.service.list_phonebook.side_effect = DatabaseServiceUnavailable()

        result = self._get(s.tenant)

        self._assert_error(result, 503, str(DatabaseServiceUnavailable()))

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


class TestContactOne(_PhonebookViewTest, _HTTPErrorChecker):

    _View = ContactOne

    def test_a_working_get(self):
        result = self.view.get(s.tenant, s.phonebook_id, s.contact_uuid)

        assert_that(result, equal_to((self.service.get_contact.return_value, 200)))

    def test_get_with_an_unknown_phonebook(self):
        self.service.get_contact.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self.view.get(s.tenant, s.phonebook_id, s.contact_uuid)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def test_get_with_an_unknown_contact(self):
        self.service.get_contact.side_effect = NoSuchContact(s.contact_uuid)

        result = self.view.get(s.tenant, s.phonebook_id, s.contact_uuid)

        self._assert_error(result, 404, 'No such contact: {}'.format(s.contact_uuid))

    def test_a_working_delete(self):

        result = self.view.delete(s.tenant, s.phonebook_id, s.contact_uuid)

        assert_that(result, equal_to(('', 204)))
        self.service.delete_contact.assert_called_once_with(s.tenant, s.phonebook_id, s.contact_uuid)

    def test_delete_with_an_unknown_phonebook(self):
        self.service.delete_contact.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self.view.delete(s.tenant, s.phonebook_id, s.contact_uuid)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def test_delete_with_an_unknown_contact(self):
        self.service.delete_contact.side_effect = NoSuchContact(s.contact_uuid)

        result = self.view.delete(s.tenant, s.phonebook_id, s.contact_uuid)

        self._assert_error(result, 404, 'No such contact: {}'.format(s.contact_uuid))

    def test_a_working_put(self):
        result = self._put(s.tenant, s.phonebook_id, s.contact_uuid, s.body)

        assert_that(result, equal_to((self.service.edit_contact.return_value, 200)))
        self.service.edit_contact.assert_called_once_with(s.tenant, s.phonebook_id, s.contact_uuid, s.body)

    def test_a_put_that_would_create_a_duplicate(self):
        self.service.edit_contact.side_effect = DuplicatedContactException

        result = self._put(s.tenant, s.phonebook_id, s.contact_uuid, s.body)

        self._assert_error(result, 409, 'Duplicating contact')

    def test_a_put_with_an_invalid_body(self):
        self.service.edit_contact.side_effect = InvalidContactException(s.error)

        result = self._put(s.tenant, s.phonebook_id, s.contact_uuid, s.body)

        self._assert_error(result, 400, str(s.error))

    def test_when_postgresql_is_down(self):
        self.service.edit_contact.side_effect = DatabaseServiceUnavailable()

        result = self._put(s.tenant, s.phonebook_id, s.contact_uuid, s.body)

        self._assert_error(result, 503, str(DatabaseServiceUnavailable()))

    def _put(self, tenant, phonebook_id, contact_uuid, body):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(json=body, args={})):
            return self.view.put(tenant, phonebook_id, contact_uuid)


class TestPhonebookOne(_PhonebookViewTest, _HTTPErrorChecker):

    _View = PhonebookOne

    def test_a_working_get(self):
        result = self.view.get(s.tenant, s.phonebook_id)

        assert_that(result, equal_to((self.service.get_phonebook.return_value, 200)))
        self.service.get_phonebook.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_get_with_an_unknown_id(self):
        phonebook_id = 42
        self.service.get_phonebook.side_effect = NoSuchPhonebook(phonebook_id)

        result = self.view.get(s.tenant, phonebook_id)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(phonebook_id))

    def test_a_working_delete(self):
        result = self.view.delete(s.tenant, s.phonebook_id)

        assert_that(result, equal_to(('', 204)))
        self.service.delete_phonebook.assert_called_once_with(s.tenant, s.phonebook_id)

    def test_delete_with_an_unknown_id(self):
        phonebook_id = 1
        self.service.delete_phonebook.side_effect = NoSuchPhonebook(phonebook_id)

        result = self.view.delete(s.tenant, phonebook_id)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(phonebook_id))

    def test_a_working_put(self):
        result = self._put(s.tenant, s.phonebook_id, s.body)

        assert_that(result, equal_to((self.service.edit_phonebook.return_value, 200)))
        self.service.edit_phonebook.assert_called_once_with(s.tenant, s.phonebook_id, s.body)

    def test_put_with_an_unknown_id(self):
        self.service.edit_phonebook.side_effect = NoSuchPhonebook(s.phonebook_id)

        result = self._put(s.tenant, s.phonebook_id, s.body)

        self._assert_error(result, 404, 'No such phonebook: {}'.format(s.phonebook_id))

    def test_put_with_an_invalid_body(self):
        self.service.edit_phonebook.side_effect = InvalidPhonebookException(s.error)

        result = self._put(s.tenant, s.phonebook_id, s.body)

        self._assert_error(result, 400, str(s.error))

    def test_a_put_that_would_create_a_duplicate(self):
        self.service.edit_phonebook.side_effect = DuplicatedPhonebookException

        result = self._put(s.tenant, s.phonebook_id, s.body)

        self._assert_error(result, 409, 'Duplicating phonebook')

    def test_when_postgresql_is_down(self):
        self.service.edit_phonebook.side_effect = DatabaseServiceUnavailable()

        result = self._put(s.tenant, s.phonebook_id, s.body)

        self._assert_error(result, 503, str(DatabaseServiceUnavailable()))

    def _put(self, tenant, phonebook_id, body):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(json=body, args={})):
            return self.view.put(tenant, phonebook_id)


class TestContactImport(_PhonebookViewTest, _HTTPErrorChecker):

    _View = ContactImport

    def test_a_valid_import(self):
        self.service.import_contacts.return_value = s.created, s.errors
        body = u'''\
firstname,lastname,number
Föo,Bar,1111
Alicé,AAA,2222
Bob,BBB,3333
'''.encode('utf-8')

        as_list = [
            {'firstname': u'Föo', 'lastname': 'Bar', 'number': '1111'},
            {'firstname': u'Alicé', 'lastname': 'AAA', 'number': '2222'},
            {'firstname': 'Bob', 'lastname': 'BBB', 'number': '3333'},
        ]

        result = self._post(s.tenant, s.phonebook_id, body, 'utf-8')

        assert_that(result, has_entries(created=s.created,
                                        failed=s.errors))
        self.service.import_contacts.assert_called_once_with(s.tenant, s.phonebook_id, as_list)

    def test_with_an_unknown_charset(self):
        body = u'''\
firstname,lastname,number
Föo,Bar,1111
Alicé,AAA,2222
Bob,BBB,3333
'''.encode('utf-8')

        result = self._post(s.tenant, s.phonebook_id, body, 'unknown')

        self._assert_error(result, 400, 'unknown encoding: unknown')

    def _post(self, tenant, phonebook_id, body, charset):
        with patch('xivo_dird.plugins.phonebook_view.request', Mock(data=body,
                                                                    args={},
                                                                    mimetype_params={'charset': charset})):
            return self.view.post(tenant, phonebook_id)


class TestArgParser(unittest.TestCase):

    def test_that_an_invalid_offset_will_raise(self):
        invalid_offsets = ['foobar', -1, '-1']
        for offset in invalid_offsets:
            assert_that(calling(ArgParser).with_args({'offset': offset}),
                        raises(InvalidArgumentError), 'Should have raised for {}'.format(offset))

    def test_that_an_invalid_limit_will_raise(self):
        invalid_limits = ['foobar', -1, '-1']
        for limit in invalid_limits:
            assert_that(calling(ArgParser).with_args({'limit': limit}),
                        raises(InvalidArgumentError), 'Should have raised for {}'.format(limit))

    def test_that_direction_should_be_asc_or_desc(self):
        invalid_directions = ['ascending', 'up', 'descending', -1]
        for direction in invalid_directions:
            assert_that(calling(ArgParser).with_args({'direction': direction}),
                        raises(InvalidArgumentError), 'Should have raised for {}'.format(direction))
