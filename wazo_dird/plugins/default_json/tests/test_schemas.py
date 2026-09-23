# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import assert_that, calling, equal_to, has_key, raises
from marshmallow import ValidationError

from ..schemas import lookup_query_string_schema


class TestLookupQueryStringSchema(unittest.TestCase):
    def test_that_a_term_is_loaded(self):
        result = lookup_query_string_schema.load({'term': 'alice'})

        assert_that(result['term'], equal_to('alice'))

    def test_that_an_empty_term_is_rejected(self):
        assert_that(
            calling(lookup_query_string_schema.load).with_args({'term': ''}),
            raises(ValidationError),
        )

    def test_that_a_missing_term_is_rejected(self):
        assert_that(
            calling(lookup_query_string_schema.load).with_args({}),
            raises(ValidationError),
        )

    def test_that_the_error_points_at_the_term_field(self):
        try:
            lookup_query_string_schema.load({'term': ''})
        except ValidationError as e:
            assert_that(e.messages, has_key('term'))
        else:
            self.fail('an empty term should not validate')

    def test_that_unknown_query_string_arguments_are_ignored(self):
        result = lookup_query_string_schema.load({'term': 'alice', 'unknown': 'value'})

        assert_that(result, equal_to({'term': 'alice'}))
