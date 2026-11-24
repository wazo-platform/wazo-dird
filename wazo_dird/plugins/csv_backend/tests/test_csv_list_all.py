# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import tempfile
import unittest
from typing import cast

from hamcrest import assert_that, calling, contains_exactly, has_entries, raises

from wazo_dird.exception import SourceListError
from wazo_dird.plugins.base_plugins import SourcePluginDependencies

from ..plugin import CSVPlugin

CONTENT = '''\
clientno,firstname,lastname
1,Alice,AAA
2,Bob,BBB
3,Charles,CCC
'''


class TestCSVListAll(unittest.TestCase):
    def setUp(self):
        fd, self.fname = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write(CONTENT)
        self.addCleanup(lambda: os.path.exists(self.fname) and os.remove(self.fname))

    def _load(self, **extra):
        source = CSVPlugin()
        config = {
            'file': self.fname,
            'name': 'my_csv',
            'unique_column': 'clientno',
            # no searched_columns: list_all does not search
            **extra,
        }
        source.load(cast(SourcePluginDependencies, {'config': config}))
        source.name = 'my_csv'
        return source

    def test_list_all_returns_every_row(self):
        source = self._load()

        results = source.list_all()

        assert_that(
            [r.fields for r in results],
            contains_exactly(
                has_entries(firstname='Alice'),
                has_entries(firstname='Bob'),
                has_entries(firstname='Charles'),
            ),
        )

    def test_list_all_raises_when_the_file_is_missing(self):
        source = self._load()
        os.remove(self.fname)

        assert_that(calling(source.list_all), raises(SourceListError))

    def test_list_all_raises_when_the_file_is_unreadable(self):
        os.chmod(self.fname, 0)
        if os.access(self.fname, os.R_OK):
            self.skipTest('running as a user that reads every file')
        source = CSVPlugin()
        source.load(
            cast(
                SourcePluginDependencies,
                {'config': {'file': self.fname, 'name': 'my_csv'}},
            )
        )
        source.name = 'my_csv'

        assert_that(calling(source.list_all), raises(SourceListError))

    def test_list_all_raises_without_a_file_configured(self):
        source = CSVPlugin()
        source.load(cast(SourcePluginDependencies, {'config': {'name': 'my_csv'}}))
        source.name = 'my_csv'

        assert_that(calling(source.list_all), raises(SourceListError))
