# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
# SPDX-License-Identifier: GPL-3.0+

from .base_dird_integration_test import BaseDirdIntegrationTest

from hamcrest import assert_that
from hamcrest import contains_inanyorder
from hamcrest import equal_to
from hamcrest import matches_regexp


class TestPersonalExport(BaseDirdIntegrationTest):

    asset = 'personal_only'

    def tearDown(self):
        self.purge_personal()

    def test_that_export_empty_returns_204(self):
        result = self.export_personal_result('valid-token')
        assert_that(result.status_code, equal_to(204))

    def test_that_export_full_returns_all_contacts(self):
        self.post_personal({'firstname': 'Alice', 'lastname': 'Aldertion'})
        self.post_personal({'firstname': 'Bob', 'lastname': 'Bodkartan'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp('Alice,[^,]*,Aldertion'),
                                                      matches_regexp('Bob,[^,]*,Bodkartan')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_with_empty_values_returns_empty_strings(self):
        self.post_personal({'firstname': 'Alice', 'lastname': ''})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp('Alice,[^,]*,$')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_full_mixes_all_headers(self):
        self.post_personal({'firstname': 'Alice'})
        self.post_personal({'lastname': 'Bodkartan'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp('Alice,[^,]*,'),
                                                      matches_regexp(',[^,]*,Bodkartan')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_with_non_ascii_is_ok(self):
        self.post_personal({'firstname': u'Éloïse'})

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp(u'Éloïse,[^,]*')))
        assert_that(result[-1], equal_to(''))

    def test_that_export_produces_the_same_output_as_import_with_empty_column(self):
        self.import_personal('firstname,lastname,special-key\njohn,doe,\nbob,martin,')

        result = self.export_personal()

        result = result.split('\r\n')
        assert_that(result[0], equal_to('firstname,id,lastname,special-key'))
        assert_that(result[1:-1], contains_inanyorder(matches_regexp(u'john,[^,]*,doe,'),
                                                      matches_regexp(u'bob,[^,]*,martin,')))
        assert_that(result[-1], equal_to(''))
