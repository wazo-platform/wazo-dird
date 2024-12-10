# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock, patch
from unittest.mock import sentinel as s

from hamcrest import assert_that, equal_to

from wazo_dird.exception import InvalidConfigError

from ..plugin import PhonebookPlugin, make_result_class


class TestDirdPhonebook(unittest.TestCase):
    def setUp(self):
        self.source = PhonebookPlugin()
        self.SourceResult = self.source._SourceResult = make_result_class(
            'test', 'id', {}
        )
        self.engine = self.source._search_engine = Mock()

    def test_load_with_phonebook_uuid(self):
        with patch(f'{PhonebookPlugin.__module__}.Session'):
            self.source.load(
                {
                    'config': {
                        'name': 'test-load',
                        'tenant_uuid': '123',
                        'phonebook_uuid': '456',
                    }
                }
            )

    def test_load_with_no_phonebook_uuid(self):
        with patch(f'{PhonebookPlugin.__module__}.Session'):
            with self.assertRaises(InvalidConfigError):
                self.source.load(
                    {'config': {'name': 'test-load', 'tenant_uuid': '123'}}
                )

    def test_that_the_id_is_used_if_supplied(self):
        id_ = self.source._get_phonebook_key(
            s.tenant_uuid, {'phonebook_uuid': "some-uuid"}
        )

        assert_that(id_, equal_to({'uuid': "some-uuid"}))

    def test_with_an_existing_phonebook_by_name(self):
        phonebooks = [
            {'id': 1, 'uuid': 'some-uuid', 'name': 'foo'},
            {'id': 2, 'uuid': 'some-other-uuid', 'name': 'bar'},
        ]

        with patch.object(
            self.source, '_crud', Mock(list=Mock(return_value=phonebooks))
        ):
            id_ = self.source._get_phonebook_key(s.tenant_uuid, {'name': 'bar'})

        assert_that(id_, equal_to({'uuid': 'some-other-uuid'}))

    def test_that_find_first_returns_a_formated_result(self):
        raw_result = self.engine.find_first_contact.return_value = {
            'id': "42",
            'name': 'foobar',
        }

        result = self.source.first_match(s.term)

        assert_that(result, equal_to(self.SourceResult(raw_result)))

    def test_that_find_first_returns_none_when_empty_result(self):
        self.engine.find_first_contact.return_value = None

        result = self.source.first_match(s.term)

        assert_that(result, equal_to(None))
