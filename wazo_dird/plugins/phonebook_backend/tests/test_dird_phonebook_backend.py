# Copyright 2016-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from collections import defaultdict
import unittest
from unittest.mock import MagicMock, Mock, patch
from unittest.mock import sentinel as s

from hamcrest import assert_that, equal_to

from ..plugin import PhonebookPlugin, make_result_class


def mock_dict(prototype):
    return defaultdict(MagicMock, prototype)


class TestDirdPhonebook(unittest.TestCase):
    def setUp(self):
        self.source = PhonebookPlugin()
        self.SourceResult = self.source._SourceResult = make_result_class(
            'test', 'id', {}
        )
        self.engine = self.source._search_engine = Mock()

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

    def test_load(self):
        with patch(
            f'{self.source.__class__.__module__}.database.PhonebookCRUD', MagicMock()
        ) as dao_mock:
            dao_mock.list.return_value = [
                mock_dict({'uuid': s.phonebook_uuid, 'name': 'test'})
            ]
            self.source.load(
                mock_dict(
                    {
                        'config': {
                            'name': 'test',
                            'phonebook_uuid': s.phonebook_uuid,
                            'tenant_uuid': s.tenant_uuid,
                            'uuid': s.source_uuid,
                        }
                    }
                )
            )
            dao_mock.assert_called_once()
