# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import unittest
import yaml

from hamcrest import (
    assert_that,
    contains,
    contains_inanyorder,
    has_entries,
)

from .base_dird_integration_test import (
    absolute_file_name,
    BackendWrapper,
)


class _BaseCSVFileTestCase(unittest.TestCase):

    def setUp(self):
        config_file = absolute_file_name(self.asset, self.source_config)
        with open(config_file) as f:
            config = {'config': yaml.load(f)}
        config['config']['file'] = absolute_file_name(self.asset, config['config']['file'][1:])
        self.backend = BackendWrapper('csv', config)


class TestCSVBackend(_BaseCSVFileTestCase):

    asset = 'csv_with_multiple_displays'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._alice = {'id': '1', 'fn': 'Alice', 'ln': 'AAA', 'num': '5555555555'}
        self._charles = {'id': '3', 'fn': 'Charles', 'ln': 'CCC', 'num': '555123555'}
        super(TestCSVBackend, self).setUp()

    def test_that_searching_for_lice_return_Alice(self):
        result = self.backend.search('lice')

        assert_that(result, contains(has_entries(**self._alice)))

    def test_reverse_lookup(self):
        result = self.backend.first('5555555555')

        assert_that(result, has_entries(**self._alice))

    def test_that_listing_by_ids_works(self):
        unknown_id = '42'

        result = self.backend.list([self._alice['id'], self._charles['id'], unknown_id])

        assert_that(result, contains_inanyorder(has_entries(**self._alice),
                                                has_entries(**self._charles)))


class TestCSVNoUnique(_BaseCSVFileTestCase):

    asset = 'csv_with_no_unique_column'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._alice = {'fn': 'Alice', 'ln': 'AAA', 'num': '5555555555'}
        super(TestCSVNoUnique, self).setUp()

    def test_lookup_should_work_without_unique_column(self):
        result = self.backend.search('lice')

        assert_that(result, contains(has_entries(**self._alice)))


class TestCSVWithAccents(_BaseCSVFileTestCase):

    asset = 'csv_with_no_unique_column'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._pepe = {'fn': 'Pépé', 'ln': 'lol', 'num': '555'}
        super(TestCSVWithAccents, self).setUp()

    def test_lookup_with_accents_in_term(self):
        result = self.backend.search('pép')

        assert_that(result, contains(has_entries(**self._pepe)))

    def test_lookup_with_accents_in_the_result(self):
        result = self.backend.search('lol')

        assert_that(result, contains(has_entries(**self._pepe)))


class TestCSVSeparator(_BaseCSVFileTestCase):

    asset = 'csv_with_pipes'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._alice = {'fn': 'Alice', 'ln': 'AAA', 'num': '5555555555'}
        super(TestCSVSeparator, self).setUp()

    def test_lookup_with_pipe(self):
        result = self.backend.search('al')

        assert_that(result, contains(has_entries(**self._alice)))
