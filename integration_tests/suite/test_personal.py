# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid
from unittest.mock import ANY

from hamcrest import (
    all_of,
    assert_that,
    contains,
    contains_inanyorder,
    empty,
    equal_to,
    has_entries,
    has_entry,
    has_item,
    has_items,
    has_key,
    has_properties,
    is_,
    none,
    not_,
)
from wazo_auth_client import Client as AuthClient
from wazo_test_helpers import until
from wazo_test_helpers.auth import AuthClient as MockAuthClient
from wazo_test_helpers.auth import MockUserToken
from wazo_test_helpers.bus import BusClient

from .helpers.base import BaseDirdIntegrationTest, PersonalOnlyTestCase
from .helpers.constants import (
    MAIN_TENANT,
    MAIN_USER_UUID,
    VALID_TOKEN_1,
    VALID_TOKEN_2,
    VALID_TOKEN_MAIN_TENANT,
    VALID_UUID,
    VALID_UUID_1,
)


class TestListPersonal(PersonalOnlyTestCase):
    def test_that_listing_empty_personal_returns_empty_list(self):
        result = self.list_personal()

        assert_that(result['items'], contains())


class TestDeletedUser(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def setUp(self):
        super().setUp()
        until.true(self.bus_is_up, tries=10)
        bus_port = self.service_port(5672, 'rabbitmq')
        self.bus = BusClient.from_connection_fields(
            host='127.0.0.1',
            port=bus_port,
            exchange_name='wazo-headers',
            exchange_type='headers',
        )
        until.true(self.bus.is_up, timeout=5)

    def test_that_deleting_a_user_deletes_its_storage(self):
        def check():
            result = self.list_personal()
            assert_that(result['items'], empty())

        check()

        self.post_personal({'firstname': 'Alice'})
        self._publish_user_deleted_event(MAIN_USER_UUID)

        until.assert_(check, tries=3)

    def _publish_user_deleted_event(self, uuid):
        payload = {
            'data': {
                'id': 42,
                'uuid': str(uuid),
            }
        }
        self.bus.publish(
            payload,
            headers={
                'name': 'user_deleted',
                'tenant_uuid': MAIN_TENANT,
                f'user_uuid:{uuid}': True,
            },
        )


class TestAddPersonal(PersonalOnlyTestCase):
    def test_that_a_token_with_no_user_uuid_returns_401(self):
        mock_auth_client = MockAuthClient('127.0.0.1', self.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        invalid_token_uuid = str(uuid.uuid4())
        invalid_token = MockUserToken.some_token(
            token=invalid_token_uuid,
            metadata={'uuid': None, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(invalid_token)

        result = self.post_personal_result(
            {'firstname': 'Alice'}, token=invalid_token_uuid
        )
        assert_that(result, has_properties(status_code=401))

    def test_that_created_personal_has_an_id(self):
        alice = self.post_personal({'firstname': 'Alice'})
        bob = self.post_personal({'firstname': 'Bob'})

        assert_that(alice['id'], not_(equal_to(bob['id'])))

    def test_that_created_personal_are_listed(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.list_personal()

        assert_that(
            result['items'],
            has_items(has_entry('firstname', 'Alice'), has_entry('firstname', 'Bob')),
        )

    def test_that_created_personal_with_non_ascii_are_listed(self):
        self.post_personal({'firstname': 'Alice', 'key': 'NonAsciiValue-é'})

        raw = self.list_personal()
        formatted = self.get_personal_with_profile('default')

        assert_that(raw['items'], has_items(has_entry('key', 'NonAsciiValue-é')))
        assert_that(
            formatted['results'],
            has_items(has_entry('column_values', contains('Alice', None, None, False))),
        )

    def test_that_adding_invalid_personal_returns_400(self):
        result = self.post_personal_result({'': 'invalid'}, VALID_TOKEN_MAIN_TENANT)

        assert_that(result.status_code, equal_to(400))

    def test_that_adding_duplicated_personal_returns_409(self):
        self.post_personal_result({'firstname': 'Alice'}, VALID_TOKEN_MAIN_TENANT)
        result = self.post_personal_result(
            {'firstname': 'Alice'}, VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(409))

    def test_that_adding_personal_with_weird_attributes_is_ok(self):
        self.post_personal({'%': '%', '?': '?', '#': '#', '%': '%'})

        result = self.list_personal()

        assert_that(
            result['items'],
            has_item(has_entries({'%': '%', '?': '?', '#': '#', '%': '%'})),
        )


class TestRemovePersonal(PersonalOnlyTestCase):
    def test_that_a_token_with_no_user_uuid_returns_401(self):
        mock_auth_client = MockAuthClient('127.0.0.1', self.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        invalid_token_uuid = str(uuid.uuid4())
        invalid_token = MockUserToken.some_token(
            token=invalid_token_uuid,
            metadata={'uuid': None, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(invalid_token)

        result = self.delete_personal_result('unknown-id', token=invalid_token_uuid)
        assert_that(result, has_properties(status_code=401))

    def test_that_removing_unknown_personal_returns_404(self):
        result = self.delete_personal_result('unknown-id', VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(404))

    def test_that_removed_personal_are_not_listed(self):
        self.post_personal({'firstname': 'Alice'})
        bob = self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})
        self.delete_personal(bob['id'])

        result = self.list_personal()

        assert_that(
            result['items'],
            contains_inanyorder(
                has_entry('firstname', 'Alice'), has_entry('firstname', 'Charlie')
            ),
        )


class TestPurgePersonal(PersonalOnlyTestCase):
    def test_that_a_token_with_no_user_uuid_returns_401(self):
        mock_auth_client = MockAuthClient('127.0.0.1', self.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        invalid_token_uuid = str(uuid.uuid4())
        invalid_token = MockUserToken.some_token(
            token=invalid_token_uuid,
            metadata={'uuid': None, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(invalid_token)

        result = self.purge_personal_result(token=invalid_token_uuid)
        assert_that(result, has_properties(status_code=401))

    def test_that_purged_personal_are_empty(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Charlie'})
        self.purge_personal()

        result = self.list_personal()

        assert_that(result['items'], empty())


class TestPersonalPersistence(PersonalOnlyTestCase):
    def test_that_personal_are_saved_across_dird_restart(self):
        self.post_personal({'firstname': 'Foo'})

        result_before = self.list_personal()

        assert_that(result_before['items'], contains(has_key('id')))

        self._run_cmd('docker-compose kill dird')
        self._run_cmd('docker-compose rm -f dird')
        self._run_cmd('docker-compose run --rm sync')

        result_after = self.list_personal()

        assert_that(result_after['items'], contains(has_key('id')))
        assert_that(
            result_before['items'][0]['id'], equal_to(result_after['items'][0]['id'])
        )


class TestPersonalVisibility(PersonalOnlyTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_auth_client = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        valid_token_1 = MockUserToken.some_token(
            token=VALID_TOKEN_1, metadata={'tenant_uuid': tenant_uuid}
        )
        valid_token_2 = MockUserToken.some_token(
            token=VALID_TOKEN_2, metadata={'tenant_uuid': tenant_uuid}
        )
        mock_auth_client.set_token(valid_token_1)
        mock_auth_client.set_token(valid_token_2)
        mock_auth_client.set_tenants({'items': [{'uuid': tenant_uuid}]})

    def test_that_personal_are_only_visible_for_the_same_token(self):
        self.post_personal({'firstname': 'Alice'}, token=VALID_TOKEN_1)
        self.post_personal({'firstname': 'Bob'}, token=VALID_TOKEN_1)
        self.post_personal({'firstname': 'Charlie'}, token=VALID_TOKEN_2)

        result_1 = self.list_personal(token=VALID_TOKEN_1)
        result_2 = self.list_personal(token=VALID_TOKEN_2)

        assert_that(
            result_1['items'],
            contains_inanyorder(
                has_entry('firstname', 'Alice'), has_entry('firstname', 'Bob')
            ),
        )
        assert_that(result_2['items'], contains(has_entry('firstname', 'Charlie')))


class TestPersonalListWithProfile(PersonalOnlyTestCase):
    def test_listing_personal_with_unknow_profile(self):
        result = self.get_personal_with_profile_result(
            'unknown', token=VALID_TOKEN_MAIN_TENANT
        )

        assert_that(result.status_code, equal_to(404))

    def test_that_listing_personal_with_profile_empty_returns_empty_list(self):
        result = self.get_personal_with_profile('default')

        assert_that(result['results'], contains())

    def test_listing_personal_with_profile(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})

        result = self.get_personal_with_profile('default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Alice', None, None, False)),
                has_entry('column_values', contains('Bob', None, None, False)),
            ),
        )


class TestLookupPersonal(PersonalOnlyTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock_auth_client = MockAuthClient('127.0.0.1', cls.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        try:
            auth_port = cls.service_port(9497, 'auth')
            auth_client = AuthClient('127.0.0.1', auth_port, prefix=None, https=False)
            auth_client.users.new(
                uuid=VALID_UUID_1, tenant_uuid=MAIN_TENANT, username='foobar2'
            )
        except Exception:
            pass
        valid_token_1 = MockUserToken(
            token=VALID_TOKEN_1,
            user_uuid=VALID_UUID_1,
            metadata={'uuid': VALID_UUID_1, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(valid_token_1)

    def setUp(self):
        super().setUp()
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Bob'})
        self.post_personal({'firstname': 'Céline'})
        self.post_personal({'firstname': 'Etienne'})
        self.post_personal({'firstname': 'john', 'lastname': 'john', 'company': 'john'})
        self.post_personal({'firstname': 'empty-column', 'lastname': ''})
        self.post_personal(
            {'firstname': 'Elice', 'lastname': 'Wowo', 'number': '123456'}
        )
        self.post_personal(
            {'firstname': 'William', 'lastname': 'Gates', 'number': '222222'},
            token=VALID_TOKEN_1,
        )

    def tearDown(self):
        self.purge_personal(token=VALID_TOKEN_1)
        super().tearDown()

    def test_that_lookup_includes_personal_contacts(self):
        result = self.lookup('ali', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Alice', None, None, False))
            ),
        )

    def test_that_lookup_accepts_non_ascii_in_term(self):
        result = self.lookup('Céline', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Céline', None, None, False))
            ),
        )

    def test_that_lookup_matches_query_ascii_with_result_non_ascii(self):
        result = self.lookup('celine', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Céline', None, None, False))
            ),
        )

    def test_that_lookup_matches_query_non_ascii_with_result_ascii(self):
        result = self.lookup('étienne', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('Etienne', None, None, False))
            ),
        )

    def test_that_lookup_does_not_return_duplicates_when_matching_multiple_fields(self):
        result = self.lookup('john', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('john', 'john', None, False))
            ),
        )

    def test_that_lookup_returns_None_when_a_column_is_empty(self):
        result = self.lookup('empty', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry('column_values', contains('empty-column', None, None, False))
            ),
        )

    def test_reverse_lookup_with_user_uuid(self):
        result = self.reverse('123456', 'default', MAIN_USER_UUID)

        assert_that(result['display'], equal_to('Elice Wowo'))

    def test_reverse_lookup_with_invalid_user_uuid(self):
        result = self.reverse('123456', 'default', 'invalid_uuid')

        assert_that(result['display'], is_(none()))

    def test_lookup_user_only_uuid_visible(self):
        result = self.lookup_user('Wil', 'default', VALID_UUID_1)

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entry(
                    'column_values', contains('William', 'Gates', '222222', False)
                )
            ),
        )
        result = self.lookup_user('Will', 'default', VALID_UUID)
        assert_that(
            result['results'],
            not_(
                contains_inanyorder(
                    has_entry(
                        'column_values', contains('William', 'Gates', '222222', False)
                    )
                )
            ),
        )


class TestEditPersonal(PersonalOnlyTestCase):
    def test_that_a_token_with_no_user_uuid_returns_401(self):
        mock_auth_client = MockAuthClient('127.0.0.1', self.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        invalid_token_uuid = str(uuid.uuid4())
        invalid_token = MockUserToken.some_token(
            token=invalid_token_uuid,
            metadata={'uuid': None, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(invalid_token)

        result = self.put_personal_result(
            'unknown-id', {'firstname': 'new'}, token=invalid_token_uuid
        )
        assert_that(result, has_properties(status_code=401))

    def test_that_edit_inexisting_personal_contact_returns_404(self):
        body = {'firstname': 'John', 'lastname': 'Doe'}
        result = self.put_personal_result('unknown-id', body, VALID_TOKEN_MAIN_TENANT)

        assert_that(result.status_code, equal_to(404))

    def test_that_edit_personal_contact_replaces_attributes(self):
        contact = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon'})
        put_result = self.put_personal(
            contact['id'], {'firstname': 'Nicolas', 'company': 'acme'}
        )

        assert_that(put_result, has_key('id'))
        assert_that(put_result, contains_inanyorder('id', 'firstname', 'company'))
        assert_that(
            put_result, has_entries({'firstname': 'Nicolas', 'company': 'acme'})
        )

        list_result = self.list_personal()
        assert_that(
            list_result['items'],
            contains(
                all_of(
                    contains_inanyorder('id', 'firstname', 'company'),
                    has_entries({'firstname': 'Nicolas', 'company': 'acme'}),
                )
            ),
        )

    def test_that_edit_cannot_duplicate_contacts(self):
        contact_1 = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon'})
        self.post_personal({'firstname': 'Paul', 'lastname': 'Narvidon'})
        put_result = self.put_personal_result(
            contact_1['id'],
            {'firstname': 'Paul', 'lastname': 'Narvidon'},
            VALID_TOKEN_MAIN_TENANT,
        )
        assert_that(put_result.status_code, equal_to(409))

        list_result = self.list_personal()
        assert_that(
            list_result['items'],
            contains_inanyorder(
                {'id': ANY, 'firstname': 'Noémie', 'lastname': 'Narvidon'},
                {'id': ANY, 'firstname': 'Paul', 'lastname': 'Narvidon'},
            ),
        )


class TestEditInvalidPersonal(PersonalOnlyTestCase):
    def test_that_edit_personal_contact_with_invalid_values_return_404(self):
        contact = self.post_personal({'firstname': 'Ursule', 'lastname': 'Uparlende'})

        result = self.put_personal_result(
            contact['id'],
            {'firstname': 'Ulga', 'company': 'acme', '': 'invalid'},
            VALID_TOKEN_MAIN_TENANT,
        )
        assert_that(result.status_code, equal_to(400))


class TestGetPersonal(PersonalOnlyTestCase):
    def test_that_a_token_with_no_user_uuid_returns_401(self):
        mock_auth_client = MockAuthClient('127.0.0.1', self.service_port(9497, 'auth'))
        tenant_uuid = MAIN_TENANT
        invalid_token_uuid = str(uuid.uuid4())
        invalid_token = MockUserToken.some_token(
            token=invalid_token_uuid,
            metadata={'uuid': None, 'tenant_uuid': tenant_uuid},
        )
        mock_auth_client.set_token(invalid_token)

        result = self.get_personal_result('unknown-id', token=invalid_token_uuid)
        assert_that(result, has_properties(status_code=401))

    def test_that_get_inexisting_personal_contact_returns_404(self):
        result = self.get_personal_result('unknown-id', VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(404))

    def test_that_get_returns_all_attributes(self):
        contact = self.post_personal({'firstname': 'Noémie', 'lastname': 'Narvidon'})

        result = self.get_personal(contact['id'])

        assert_that(
            result, has_entries({'firstname': 'Noémie', 'lastname': 'Narvidon'})
        )

    def test_that_personal_api_is_symmetric(self):
        contact_post = self.post_personal(
            {'firstname': 'Noémie', 'lastname': 'Narvidon', 'special-key': ''}
        )
        contact_put = self.put_personal(contact_post['id'], contact_post)
        contact_get = self.get_personal(contact_post['id'])

        assert_that(contact_get, equal_to(contact_post))
        assert_that(contact_get, equal_to(contact_put))


class TestSearchPersonal(PersonalOnlyTestCase):
    def setUp(self):
        super().setUp()
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'firstname': 'Etienne'})
        self.post_personal({'firstname': 'Céline'})
        self.post_personal({'firstname': 'Ãlberto'})
        self.post_personal({'firstname': 'Bob'})

    def test_that_search_ordered_returns_right_order(self):
        result = self.list_personal(order='firstname')
        assert_that(
            result['items'],
            contains(
                has_entry('firstname', 'Alice'),
                has_entry('firstname', 'Ãlberto'),
                has_entry('firstname', 'Bob'),
                has_entry('firstname', 'Céline'),
                has_entry('firstname', 'Etienne'),
            ),
        )

        result = self.list_personal(order='firstname', direction='desc')
        assert_that(
            result['items'],
            contains(
                has_entry('firstname', 'Etienne'),
                has_entry('firstname', 'Céline'),
                has_entry('firstname', 'Bob'),
                has_entry('firstname', 'Ãlberto'),
                has_entry('firstname', 'Alice'),
            ),
        )

        wrong_column = 'invalid'
        response = self.list_personal_result(
            VALID_TOKEN_MAIN_TENANT, order=wrong_column
        )
        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json(),
            has_entry('reason', f"order: column '{wrong_column}' was not found"),
        )

        wrong_direction = 'invalid'
        response = self.list_personal_result(
            VALID_TOKEN_MAIN_TENANT, direction=wrong_direction
        )
        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json(), has_entry('reason', 'direction must be asc or desc')
        )

    def test_that_search_limited_returns_right_number(self):
        result = self.list_personal(order='firstname', limit=2)
        assert_that(
            result['items'],
            contains(
                has_entry('firstname', 'Alice'),
                has_entry('firstname', 'Ãlberto'),
            ),
        )
