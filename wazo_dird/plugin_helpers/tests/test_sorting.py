# Copyright 2020-2025 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, contains_exactly

from ..sorting import sort_contacts


class TestOffice365Service(unittest.TestCase):
    def test_sort(self) -> None:
        a = {
            'firstname': 'a',
            'lastname': 'z',
            'exten': '1001',
        }
        b = {
            'firstname': 'b',
            'lastname': 'y',
            'exten': '1002',
        }
        c = {
            'firstname': 'c',
            'lastname': None,
            'exten': '1003',
        }

        result = sort_contacts([b, c, a])
        assert_that(result, contains_exactly(b, c, a))

        result = sort_contacts([b, c, a], order='firstname')
        assert_that(result, contains_exactly(a, b, c))

        result = sort_contacts([b, c, a], order='lastname')
        assert_that(result, contains_exactly(b, a, c))

        result = sort_contacts([a, b, c], order='firstname', direction='desc')
        assert_that(result, contains_exactly(c, b, a))
