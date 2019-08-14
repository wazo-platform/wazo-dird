# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import assert_that, contains, contains_inanyorder, empty, has_entries

from ..schemas import contact_list_schema


class TestContactSchema(TestCase):
    def test_dump(self):
        raw = [
            {
                'id': 3,
                'name': 'minimal',
                'extensions': [],
                'incalls': [
                    {
                        'extensions': [
                            {
                                'exten': '4001',
                                'context': 'from-extern',
                                'id': 77,
                                'links': [
                                    {'rel': 'extensions', 'href': '.../extensions/77'}
                                ],
                            }
                        ],
                        'id': 14,
                        'links': [{'rel': 'incalls', 'href': '.../incalls/14'}],
                    }
                ],
            },
            {
                'id': 1,
                'name': 'test',
                'extensions': [
                    {
                        'exten': '4001',
                        'context': 'inside',
                        'id': 57,
                        'links': [{'rel': 'extensions', 'href': '.../extensions/57'}],
                    }
                ],
                'incalls': [
                    {
                        'extensions': [
                            {
                                'exten': '1009',
                                'context': 'from-extern',
                                'id': 76,
                                'links': [
                                    {'rel': 'extensions', 'href': '.../extensions/76'}
                                ],
                            }
                        ],
                        'id': 13,
                        'links': [{'rel': 'incalls', 'href': '.../incalls/13'}],
                    }
                ],
            },
        ]

        result = contact_list_schema.dump(raw)

        assert_that(
            result,
            contains_inanyorder(
                has_entries(
                    id=3,
                    name='minimal',
                    extensions=empty(),
                    incalls=contains(has_entries(exten='4001')),
                ),
                has_entries(
                    id=1,
                    name='test',
                    extensions=contains(has_entries(exten='4001')),
                    incalls=contains(has_entries(exten='1009')),
                ),
            ),
        )
