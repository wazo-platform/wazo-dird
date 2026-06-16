# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from wazo_dird.database.queries.base import build_exten_contact_map


class TestBuildExtenContactMap(unittest.TestCase):
    def test_empty_rows_returns_empty(self):
        result = build_exten_contact_map([], ['1234'], ['number'])
        assert result == {}

    def test_single_match(self):
        rows = [
            ('uuid-1', 'number', '1234'),
            ('uuid-1', 'firstname', 'Alice'),
        ]
        result = build_exten_contact_map(rows, ['1234'], ['number'])
        assert result == {
            '1234': {'id': 'uuid-1', 'number': '1234', 'firstname': 'Alice'}
        }

    def test_all_fields_included_in_contact(self):
        rows = [
            ('uuid-1', 'number', '1234'),
            ('uuid-1', 'firstname', 'Alice'),
            ('uuid-1', 'lastname', 'Smith'),
            ('uuid-1', 'email', 'alice@example.com'),
        ]
        result = build_exten_contact_map(rows, ['1234'], ['number'])
        assert result == {
            '1234': {
                'id': 'uuid-1',
                'number': '1234',
                'firstname': 'Alice',
                'lastname': 'Smith',
                'email': 'alice@example.com',
            }
        }

    def test_multiple_extens_different_contacts(self):
        rows = [
            ('uuid-1', 'number', '1111'),
            ('uuid-1', 'firstname', 'Alice'),
            ('uuid-2', 'number', '2222'),
            ('uuid-2', 'firstname', 'Bob'),
        ]
        result = build_exten_contact_map(rows, ['1111', '2222'], ['number'])
        assert result == {
            '1111': {'id': 'uuid-1', 'number': '1111', 'firstname': 'Alice'},
            '2222': {'id': 'uuid-2', 'number': '2222', 'firstname': 'Bob'},
        }

    def test_first_contact_wins_when_two_match_same_exten(self):
        rows = [
            ('uuid-1', 'number', '1234'),
            ('uuid-1', 'firstname', 'Alice'),
            ('uuid-2', 'number', '1234'),
            ('uuid-2', 'firstname', 'Bob'),
        ]
        result = build_exten_contact_map(rows, ['1234'], ['number'])
        assert result == {
            '1234': {'id': 'uuid-1', 'number': '1234', 'firstname': 'Alice'}
        }

    def test_field_matching_exten_but_wrong_column_not_mapped(self):
        # 'email' is not in first_match_columns — should not be used to map exten
        rows = [
            ('uuid-1', 'number', '1234'),
            ('uuid-1', 'email', '5678'),
        ]
        result = build_exten_contact_map(rows, ['1234', '5678'], ['number'])
        assert '5678' not in result
        assert '1234' in result

    def test_mobile_column_also_maps_exten(self):
        rows = [
            ('uuid-1', 'number', '1111'),
            ('uuid-1', 'mobile', '9999'),
            ('uuid-1', 'firstname', 'Alice'),
        ]
        result = build_exten_contact_map(rows, ['1111', '9999'], ['number', 'mobile'])
        assert '1111' in result
        assert '9999' in result
        assert result['1111'] == result['9999']
