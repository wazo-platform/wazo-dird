# -*- coding: utf-8 -*-
# Copyright (C) 2015-2016 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

from hamcrest import all_of
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import empty
from hamcrest import equal_to
from hamcrest import has_entries
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import has_key
from hamcrest import is_
from hamcrest import none
from hamcrest import not_

from mock import ANY

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_UUID
from .base_dird_integration_test import VALID_TOKEN
from .base_dird_integration_test import VALID_TOKEN_1
from .base_dird_integration_test import VALID_TOKEN_2


class TestListPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_listing_empty_personal_returns_empty_list(self):
        result = self.list_personal()

        assert_that(result['items'], contains())


class TestAddPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_created_personal_has_an_id(self):
        alice = self.post_personal({'firstname': 'Alice'}, token=VALID_TOKEN)
        bob = self.post_personal({'firstname': 'Bob'}, token=VALID_TOKEN)

        assert_that(alice['id'], not_(equal_to(bob['id'])))

    def test_that_created_personal_are_listed(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.list_personal()

        assert_that(result['items'], has_items(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Bob')))

    def test_that_created_personal_with_non_ascii_are_listed(self):
        self.post_personal({'firstname': 'Alice', 'key': u'NonAsciiValue-é'})

        raw = self.list_personal()
        formatted = self.get_personal_with_profile('default')

        assert_that(raw['items'], has_items(
            has_entry('key', u'NonAsciiValue-é')))
        assert_that(formatted['results'], has_items(
            has_entry('column_values', contains(u'Alice', None, None, False))))

    def test_that_adding_invalid_personal_returns_400(self):
        result = self.post_personal_result({'.': 'invalid'}, VALID_TOKEN)

        assert_that(result.status_code, equal_to(400))

    def test_that_adding_personal_with_weird_attributes_is_ok(self):
        self.post_personal({
            '%': '%',
            '?': '?',
            '#': '#',
            '%': '%'
        })

        result = self.list_personal()

        assert_that(result['items'], has_item(
            has_entries({
                '%': '%',
                '?': '?',
                '#': '#',
                '%': '%'
            })))


class TestRemovePersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_removing_unknown_personal_returns_404(self):
        result = self.delete_personal_result('unknown-id', VALID_TOKEN)

        assert_that(result.status_code, equal_to(404))

    def test_that_removed_personal_are_not_listed(self):
        self.post_personal({'firstname': 'Alice'})
        bob = self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})
        self.delete_personal(bob['id'])

        result = self.list_personal()

        assert_that(result['items'], contains_inanyorder(
            has_entry('firstname', 'Alice'),
            has_entry('firstname', 'Charlie')))


class TestPurgePersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_purged_personal_are_empty(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})
        self.purge_personal()

        result = self.list_personal()

        assert_that(result['items'], empty())


class TestPersonalPersistence(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_personal_are_saved_across_dird_restart(self):
        self.post_personal({'firstname': 'Foo'})

        result_before = self.list_personal()

        assert_that(result_before['items'], contains(has_key('id')))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result_after = self.list_personal()

        assert_that(result_after['items'], contains(has_key('id')))
        assert_that(result_before['items'][0]['id'], equal_to(result_after['items'][0]['id']))


class TestPersonalVisibility(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_personal_are_only_visible_for_the_same_token(self):
        self.post_personal({'firstname': 'Alice'}, token=VALID_TOKEN_1)
        self.post_personal({'firstname': 'Bob'}, token=VALID_TOKEN_1)
        self.post_personal({'firstname': 'Charlie'}, token=VALID_TOKEN_2)

        result_1 = self.list_personal(token=VALID_TOKEN_1)
        result_2 = self.list_personal(token=VALID_TOKEN_2)

        assert_that(result_1['items'], contains_inanyorder(has_entry('firstname', 'Alice'),
                                                           has_entry('firstname', 'Bob')))
        assert_that(result_2['items'], contains(has_entry('firstname', 'Charlie')))


class TestPersonalListWithProfile(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_listing_personal_with_unknow_profile(self):
        result = self.get_personal_with_profile_result('unknown', token=VALID_TOKEN)

        assert_that(result.status_code, equal_to(404))

    def test_that_listing_personal_with_profile_empty_returns_empty_list(self):
        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains())

    def test_listing_personal_with_profile(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False)),
            has_entry('column_values', contains('Bob', None, None, False))))


class TestLookupPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    @classmethod
    def setUpClass(cls):
        super(TestLookupPersonal, cls).setUpClass()
        cls.post_personal({'firstname': 'Alice'})
        cls.post_personal({'firstname': 'Bob'})
        cls.post_personal({'firstname': 'Céline'})
        cls.post_personal({'firstname': 'Etienne'})
        cls.post_personal({'firstname': 'john', 'lastname': 'john', 'company': 'john'})
        cls.post_personal({'firstname': 'empty-column', 'lastname': ''})
        cls.post_personal({'firstname': 'Elice', 'lastname': 'Wowo', 'number': '123456'})

    def test_that_lookup_includes_personal_contacts(self):
        result = self.lookup('ali', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains('Alice', None, None, False))))

    def test_that_lookup_accepts_non_ascii_in_term(self):
        result = self.lookup(u'Céline', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Céline', None, None, False))))

    def test_that_lookup_matches_query_ascii_with_result_non_ascii(self):
        result = self.lookup(u'celine', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Céline', None, None, False))))

    def test_that_lookup_matches_query_non_ascii_with_result_ascii(self):
        result = self.lookup(u'étienne', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'Etienne', None, None, False))))

    def test_that_lookup_does_not_return_duplicates_when_matching_multiple_fields(self):
        result = self.lookup('john', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'john', 'john', None, False))))

    def test_that_lookup_returns_None_when_a_column_is_empty(self):
        result = self.lookup('empty', 'default')

        assert_that(result['results'], contains_inanyorder(
            has_entry('column_values', contains(u'empty-column', None, None, False))))

    def test_reverse_lookup_with_alias_me(self):
        result = self.reverse('123456', 'default', VALID_UUID)

        assert_that(result['display'], equal_to('Elice Wowo'))

    def test_reverse_lookup_with_xivo_user_uuid(self):
        result = self.reverse('123456', 'default', 'uuid')

        assert_that(result['display'], equal_to('Elice Wowo'))

    def test_reverse_lookup_with_invalid_xivo_user_uuid(self):
        result = self.reverse('123456', 'default', 'invalid_uuid')

        assert_that(result['display'], is_(none()))


class TestEditPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_edit_inexisting_personal_contact_returns_404(self):
        result = self.put_personal_result('unknown-id', {'firstname': 'John', 'lastname': 'Doe'}, VALID_TOKEN)

        assert_that(result.status_code, equal_to(404))

    def test_that_edit_personal_contact_replaces_attributes(self):
        contact = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon'})

        put_result = self.put_personal(contact['id'], {'firstname': 'Nicolas', 'company': 'acme'})

        assert_that(put_result, has_key('id'))
        assert_that(put_result, contains_inanyorder('id', 'firstname', 'company'))
        assert_that(put_result, has_entries({
            'firstname': 'Nicolas',
            'company': 'acme'
        }))

        list_result = self.list_personal()
        assert_that(list_result['items'], contains(all_of(
            contains_inanyorder('id', 'firstname', 'company'),
            has_entries({
                'firstname': 'Nicolas',
                'company': 'acme'
            })
        )))

    def test_that_edit_cannot_duplicate_contacts(self):
        contact_1 = self.post_personal({'firstname': u'Noémie', 'lastname': u'Narvidon'})
        self.post_personal({'firstname': u'Paul', 'lastname': u'Narvidon'})

        put_result = self.put_personal_result(contact_1['id'], {'firstname': u'Paul', 'lastname': u'Narvidon'}, VALID_TOKEN)
        assert_that(put_result.status_code, equal_to(400))

        list_result = self.list_personal()
        assert_that(list_result['items'], contains_inanyorder({'id': ANY,
                                                               'firstname': u'Noémie',
                                                               'lastname': u'Narvidon'},
                                                              {'id': ANY,
                                                               'firstname': u'Paul',
                                                               'lastname': u'Narvidon'}))


class TestEditInvalidPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_edit_personal_contact_with_invalid_values_return_404(self):
        contact = self.post_personal({'firstname': 'Ursule', 'lastname': 'Uparlende'})

        result = self.put_personal_result(contact['id'],
                                          {'firstname': 'Ulga',
                                           'company': 'acme',
                                           '.': 'invalid'},
                                          VALID_TOKEN)

        assert_that(result.status_code, equal_to(400))


class TestGetPersonal(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_get_inexisting_personal_contact_returns_404(self):
        result = self.get_personal_result('unknown-id', VALID_TOKEN)

        assert_that(result.status_code, equal_to(404))

    def test_that_get_returns_all_attributes(self):
        contact = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon'})

        result = self.get_personal(contact['id'])

        assert_that(result, has_entries({
            'firstname': u'Noémie',
            'lastname': 'Narvidon'
        }))

    def test_that_personal_api_is_symmetric(self):
        contact_post = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon', 'special-key': ''})
        contact_put = self.put_personal(contact_post['id'], contact_post)
        contact_get = self.get_personal(contact_post['id'])

        assert_that(contact_get, equal_to(contact_post))
        assert_that(contact_get, equal_to(contact_put))
