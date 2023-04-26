# Copyright 2015-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import textwrap

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    equal_to,
    has_entry,
    has_entries,
)

from .helpers.base import BaseDirdIntegrationTest
from .helpers.constants import VALID_TOKEN_MAIN_TENANT


class TestPersonalImportFail(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def test_that_import_empty_returns_400(self):
        result = self.import_personal_result('', VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_only_headers_return_400(self):
        result = self.import_personal_result(
            'firstname,lastname\n', VALID_TOKEN_MAIN_TENANT
        )
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_invalid_headers_return_400(self):
        csv = textwrap.dedent(
            '''\
            ,lastname
            alice,ablskdfj
            bob,baseoirjl
            '''
        )
        result = self.import_personal_result(csv, VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_only_wrong_entries_return_400(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            alice
            bob
            '''
        )
        result = self.import_personal_result(csv, VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(400))

    def test_that_import_ignores_superfluous_fields(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            alice,aldertion,field,field
            bob,bodkartan,field,field
            '''
        )
        result = self.import_personal_result(csv, VALID_TOKEN_MAIN_TENANT)
        assert_that(result.status_code, equal_to(400))

    def test_that_import_wrong_encoding_returns_400(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            valérie,vladinski
            loïc,lorbantic
            '''
        ).encode('cp1252')
        result = self.import_personal_result(
            csv, VALID_TOKEN_MAIN_TENANT, encoding='utf-8'
        )
        assert_that(result.status_code, equal_to(400))


class TestPersonalImportSuccess(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def test_that_import_with_correct_data_appears_in_list(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            alice,aldertion
            bob,bodkartan
            '''
        )
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT)

        assert_that(result['failed'], contains())
        assert_that(
            result['created'],
            contains_inanyorder(
                has_entries({'firstname': 'alice', 'lastname': 'aldertion'}),
                has_entries({'firstname': 'bob', 'lastname': 'bodkartan'}),
            ),
        )
        assert_that(
            result['created'], contains_inanyorder(*self.list_personal()['items'])
        )


class TestPersonalImportSomeFail(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def test_that_import_with_one_wrongly_formatted_creates_the_others(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            alice,aldertion
            i,love,commas,,,,,,,,,,,,
            bob,bodkartan
            i,too,love,commas,,,,,,,,,,,,
            '''
        )
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT)

        assert_that(
            result['failed'], contains(has_entry('line', 3), has_entry('line', 5))
        )
        assert_that(
            self.list_personal()['items'],
            contains_inanyorder(
                has_entries({'firstname': 'alice', 'lastname': 'aldertion'}),
                has_entries({'firstname': 'bob', 'lastname': 'bodkartan'}),
            ),
        )

    def test_that_importing_a_contact_with_an_existing_uuid(self):
        csv = textwrap.dedent(
            '''\
        firstname
        alice
        '''
        )
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT)
        for user in result['created']:
            uuid = user['id']
            break

        csv = textwrap.dedent(
            f'''\
        id,firstname
        {uuid},not alice
        29d4aec1-db4c-4c67-80a0-b83136c58a47,bob
        '''
        )
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT)

        assert_that(result['failed'], contains(has_entry('line', 2)))


class TestPersonalImportUTF8(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def test_that_import_with_utf8_chars_is_valid(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            valérie,vidalzami
            '''
        ).encode('utf-8')
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT)

        assert_that(
            result['created'],
            contains_inanyorder(
                has_entries({'firstname': 'valérie', 'lastname': 'vidalzami'})
            ),
        )


class TestPersonalImportCP1252(BaseDirdIntegrationTest):
    asset = 'personal_only'

    def test_that_import_with_cp1252_chars_is_valid(self):
        csv = textwrap.dedent(
            '''\
            firstname,lastname
            valérie,vidalzami
            '''
        ).encode('cp1252')
        result = self.import_personal(csv, VALID_TOKEN_MAIN_TENANT, encoding='cp1252')

        assert_that(
            result['created'],
            contains_inanyorder(
                has_entries({'firstname': 'valérie', 'lastname': 'vidalzami'})
            ),
        )
