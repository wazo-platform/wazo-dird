# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, equal_to

from wazo_dird.helpers import DisplayAwareResource, DisplayColumn

make_display = DisplayAwareResource._make_display


class TestMakeDisplays(unittest.TestCase):
    def test_that_make_displays_with_no_config_returns_empty_dict(self):
        result = make_display({})

        assert_that(result, equal_to(None))

    def test_that_make_displays_generate_display_dict(self):
        first_display = [
            DisplayColumn('Firstname', None, 'Unknown', 'firstname'),
            DisplayColumn('Lastname', None, 'ln', 'lastname'),
        ]
        second_display = [
            DisplayColumn('fn', 'some_type', 'N/A', 'firstname'),
            DisplayColumn('ln', None, 'N/A', 'LAST'),
        ]

        first = {
            'name': 'first_display',
            'columns': [
                {
                    'title': 'Firstname',
                    'type': None,
                    'default': 'Unknown',
                    'field': 'firstname',
                },
                {
                    'title': 'Lastname',
                    'type': None,
                    'default': 'ln',
                    'field': 'lastname',
                },
            ],
        }
        second = {
            'name': 'second_display',
            'columns': [
                {
                    'title': 'fn',
                    'type': 'some_type',
                    'default': 'N/A',
                    'field': 'firstname',
                },
                {'title': 'ln', 'type': None, 'default': 'N/A', 'field': 'LAST'},
            ],
        }

        assert_that(make_display(first), equal_to(first_display))
        assert_that(make_display(second), equal_to(second_display))
