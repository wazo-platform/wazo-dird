# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import unittest
import yaml

from hamcrest import assert_that, contains, contains_inanyorder, has_entries

from .helpers.base import BaseDirdIntegrationTest, CSVWithMultipleDisplayTestCase
from .helpers.config import new_csv_with_pipes_config
from .helpers.constants import VALID_UUID
from .base_dird_integration_test import absolute_file_name, BackendWrapper


class _BaseCSVFileTestCase(unittest.TestCase):
    def setUp(self):
        config_file = absolute_file_name(self.asset, self.source_config)
        with open(config_file) as f:
            config = {'config': yaml.safe_load(f)}
        config['config']['file'] = absolute_file_name(
            self.asset, config['config']['file'][1:]
        )
        self.backend = BackendWrapper('csv', config)
        super().setUp()


class TestCSVBackend(CSVWithMultipleDisplayTestCase):
    def setUp(self):
        super().setUp()
        self._alice = ['Alice', 'AAA', '5555555555']
        self._charles = ['Charles', 'CCC', '555123555']

    def test_that_searching_for_lice_return_Alice(self):
        response = self.lookup('lice', 'default')

        favorite = [False]
        assert_that(
            response['results'],
            contains(has_entries(column_values=self._alice + favorite)),
        )

    def test_that_csv_file_changes_have_been_committed(self):

        line_to_append = '4,James,XXX,222123666,achohra@example.com'
        file_to_update = os.path.join(
            self.assets_root, 'tmp', 'data', 'asset.all_routes.test.csv'
        )
        updated_column_values = ['James', 'XXX', '222123666']

        try:
            with open(file_to_update, 'a') as my_file:

                my_file.write(line_to_append)

            response = self.lookup('James', 'default')
            favorite = [False]
            assert_that(
                response['results'],
                contains(has_entries(column_values=updated_column_values + favorite)),
            )

        finally:

            with open(file_to_update, "r") as in_file:
                lines = in_file.readlines()[:-1]

            with open(file_to_update, "w+") as out_file:
                out_file.writelines(lines)

    def test_reverse_lookup(self):
        response = self.reverse('5555555555', 'default', VALID_UUID)

        expected_display = '{} {}'.format(self._alice[0], self._alice[1])
        assert_that(response, has_entries(display=expected_display))

    def test_that_listing_by_ids_works(self):
        alice_id = '1'
        charles_id = '3'
        unknown_id = '42'

        self.put_favorite('my_csv', alice_id)
        self.put_favorite('my_csv', charles_id)
        self.put_favorite('my_csv', unknown_id)

        try:
            response = self.favorites('default')

            favorite = [True]
            assert_that(
                response['results'],
                contains(
                    has_entries(column_values=self._alice + favorite),
                    has_entries(column_values=self._charles + favorite),
                ),
            )
        finally:
            self.delete_favorite('my_csv', alice_id)
            self.delete_favorite('my_csv', charles_id)
            self.delete_favorite('my_csv', unknown_id)


class TestCSVNoUnique(_BaseCSVFileTestCase):

    asset = 'csv_with_no_unique_column'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._alice = {'fn': 'Alice', 'ln': 'AAA', 'num': '5555555555'}
        super().setUp()

    def test_lookup_should_work_without_unique_column(self):
        result = self.backend.search('lice')

        assert_that(result, contains(has_entries(**self._alice)))


class TestCSVWithAccents(_BaseCSVFileTestCase):

    asset = 'csv_with_no_unique_column'
    source_config = 'etc/wazo-dird/sources.d/my_test_csv.yml'

    def setUp(self):
        self._pepe = {'fn': 'Pépé', 'ln': 'lol', 'num': '555'}
        super().setUp()

    def test_lookup_with_accents_in_term(self):
        result = self.backend.search('pép')

        assert_that(result, contains(has_entries(**self._pepe)))

    def test_lookup_with_accents_in_the_result(self):
        result = self.backend.search('lol')

        assert_that(result, contains(has_entries(**self._pepe)))


class TestCSVSeparator(BaseDirdIntegrationTest):

    asset = 'csv_with_pipes'
    config_factory = new_csv_with_pipes_config

    def test_lookup_with_pipe(self):
        result = self.lookup('al', 'default')

        assert_that(
            result['results'],
            contains_inanyorder(
                has_entries(column_values=contains('Alice', 'AAA', '5555555555'))
            ),
        )
