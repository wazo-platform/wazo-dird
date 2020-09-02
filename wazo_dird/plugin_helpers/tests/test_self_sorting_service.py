# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, contains

from ..self_sorting_service import SelfSortingServiceMixin as Service


class TestOffice365Service(unittest.TestCase):
    def test_sort(self):
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

        result = Service.sort([b, c, a])
        assert_that(result, contains(b, c, a))

        result = Service.sort([b, c, a], order='firstname')
        assert_that(result, contains(a, b, c))

        result = Service.sort([b, c, a], order='lastname')
        assert_that(result, contains(b, a, c))

        result = Service.sort([a, b, c], order='firstname', direction='desc')
        assert_that(result, contains(c, b, a))
