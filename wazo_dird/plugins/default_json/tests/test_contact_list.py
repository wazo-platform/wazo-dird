# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, calling, equal_to, has_entries, raises
from marshmallow import ValidationError

from wazo_dird import make_result_class

from ..http import _ContactListFormatter
from ..schemas import contact_list_schema

SourceResult = make_result_class('csv', 'my_csv', 'id')
PersonalResult = make_result_class('personal', 'personal', 'id', is_personal=True)


class TestContactListFormatter(unittest.TestCase):
    def test_an_item_carries_its_source_fields_relations_and_flags(self):
        result = SourceResult({'id': '1', 'name': 'Alice'}, user_uuid='u')
        formatter = _ContactListFormatter({('my_csv', '1')})

        item = formatter.format(result)

        assert_that(
            item,
            equal_to(
                {
                    'source': 'my_csv',
                    'backend': 'csv',
                    'fields': {'id': '1', 'name': 'Alice'},
                    'relations': {
                        'xivo_id': None,
                        'agent_id': None,
                        'user_id': None,
                        'user_uuid': 'u',
                        'endpoint_id': None,
                        'source_entry_id': '1',
                    },
                    'favorite': True,
                    'personal': False,
                }
            ),
        )

    def test_a_favorite_is_keyed_by_source_and_id(self):
        formatter = _ContactListFormatter({('other', '1'), ('my_csv', '2')})

        item = formatter.format(SourceResult({'id': '1'}))

        assert_that(item, has_entries(favorite=False))

    def test_a_personal_contact_is_flagged(self):
        item = _ContactListFormatter(set()).format(PersonalResult({'id': '1'}))

        assert_that(item, has_entries(personal=True, favorite=False))

    def test_the_cached_result_is_never_written(self):
        result = SourceResult({'id': '1'})

        item = _ContactListFormatter(set()).format(result)
        item['fields']['id'] = 'changed'
        item['relations']['user_uuid'] = 'changed'

        assert_that(result.fields, equal_to({'id': '1'}))
        assert_that(result.relations['user_uuid'], equal_to(None))


class TestContactListSchema(unittest.TestCase):
    def test_defaults(self):
        assert_that(contact_list_schema.load({}), equal_to({'limit': 100, 'offset': 0}))

    def test_bounds(self):
        assert_that(
            contact_list_schema.load({'limit': '1000', 'offset': '0'}),
            equal_to({'limit': 1000, 'offset': 0}),
        )
        for params in (
            {'limit': '1001'},
            {'limit': '0'},
            {'limit': '-1'},
            {'offset': '-1'},
            {'limit': 'a'},
            {'offset': 'a'},
            {'limit': '1.5'},
        ):
            assert_that(
                calling(contact_list_schema.load).with_args(params),
                raises(ValidationError),
                str(params),
            )


class TestContactListFavorites(unittest.TestCase):
    def test_a_favorite_of_any_source_is_flagged(self):
        OtherResult = make_result_class('csv', 'other', 'id')
        formatter = _ContactListFormatter({('other', '1')})

        assert_that(
            formatter.format(OtherResult({'id': '1'})), has_entries(favorite=True)
        )
        assert_that(
            formatter.format(SourceResult({'id': '1'})), has_entries(favorite=False)
        )
