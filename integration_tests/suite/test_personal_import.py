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

import textwrap

from .base_dird_integration_test import BaseDirdIntegrationTest

from hamcrest import assert_that
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_entries


class TestPersonalImportFail(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_import_empty_returns_400(self):
        result = self.import_personal_result('', 'valid-token')
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_only_headers_return_400(self):
        result = self.import_personal_result('firstname,lastname\n', 'valid-token')
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_invalid_headers_return_400(self):
        csv = textwrap.dedent('''\
            ,lastname
            alice,ablskdfj
            bob,baseoirjl
            ''')
        result = self.import_personal_result(csv, 'valid-token')
        assert_that(result.status_code, equal_to(400))

    def test_that_import_with_only_wrong_entries_return_400(self):
        csv = textwrap.dedent('''\
            firstname,lastname
            alice
            bob
            ''')
        result = self.import_personal_result(csv, 'valid-token')
        assert_that(result.status_code, equal_to(400))

    def test_that_import_ignores_superfluous_fields(self):
        csv = textwrap.dedent('''\
            firstname,lastname
            alice,aldertion,field,field
            bob,bodkartan,field,field
            ''')
        result = self.import_personal_result(csv, 'valid-token')
        assert_that(result.status_code, equal_to(400))

    def test_that_import_wrong_encoding_returns_400(self):
        csv = textwrap.dedent(u'''\
            firstname,lastname
            valérie,vladinski
            loïc,lorbantic
            '''.encode('cp1252'))
        result = self.import_personal_result(csv, 'valid-token', encoding='utf-8')
        assert_that(result.status_code, equal_to(400))


class TestPersonalImportSuccess(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_import_with_correct_data_appears_in_list(self):
        csv = textwrap.dedent('''\
            firstname,lastname
            alice,aldertion
            bob,bodkartan
            ''')
        result = self.import_personal(csv, 'valid-token')

        assert_that(result['failed'], contains())
        assert_that(result['created'], contains_inanyorder(
            has_entries({'firstname': 'alice', 'lastname': 'aldertion'}),
            has_entries({'firstname': 'bob', 'lastname': 'bodkartan'})))
        assert_that(result['created'], contains_inanyorder(*self.list_personal()['items']))


class TestPersonalImportSomeFail(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_import_with_one_wrongly_formatted_creates_the_others(self):
        csv = textwrap.dedent('''\
            firstname,lastname
            alice,aldertion
            i,love,commas,,,,,,,,,,,,
            bob,bodkartan
            i,too,love,commas,,,,,,,,,,,,
            ''')
        result = self.import_personal(csv, 'valid-token')

        assert_that(result['failed'], contains(
            has_entry('line', 3),
            has_entry('line', 5)))
        assert_that(self.list_personal()['items'], contains_inanyorder(
            has_entries({'firstname': 'alice', 'lastname': 'aldertion'}),
            has_entries({'firstname': 'bob', 'lastname': 'bodkartan'})))


class TestPersonalImportUTF8(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_import_with_utf8_chars_is_valid(self):
        csv = textwrap.dedent(u'''\
            firstname,lastname
            valérie,vidalzami
            '''.encode('utf-8'))
        result = self.import_personal(csv, 'valid-token')

        assert_that(result['created'], contains_inanyorder(
            has_entries({'firstname': u'valérie', 'lastname': 'vidalzami'})))


class TestPersonalImportCP1252(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def test_that_import_with_cp1252_chars_is_valid(self):
        csv = textwrap.dedent(u'''\
            firstname,lastname
            valérie,vidalzami
            '''.encode('cp1252'))
        result = self.import_personal(csv, 'valid-token', encoding='cp1252')

        assert_that(result['created'], contains_inanyorder(
            has_entries({'firstname': u'valérie', 'lastname': 'vidalzami'})))
