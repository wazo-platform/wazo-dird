# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import assert_that, calling, has_entries, raises
from marshmallow.exceptions import ValidationError

from ..schemas import ServiceOptionsSchema

_schema = ServiceOptionsSchema()


class TestServiceOptionsSchema(TestCase):
    def test_empty_options_is_valid(self):
        result = _schema.load({})
        assert_that(result, has_entries(timeout=None))

    def test_valid_timeout(self):
        result = _schema.load({'timeout': 1.5})
        assert_that(result, has_entries(timeout=1.5))

    def test_null_timeout_is_valid(self):
        result = _schema.load({'timeout': None})
        assert_that(result, has_entries(timeout=None))

    def test_zero_timeout_raises(self):
        assert_that(
            calling(_schema.load).with_args({'timeout': 0}),
            raises(ValidationError),
        )

    def test_negative_timeout_raises(self):
        assert_that(
            calling(_schema.load).with_args({'timeout': -1}),
            raises(ValidationError),
        )

    def test_unknown_key_raises(self):
        assert_that(
            calling(_schema.load).with_args({'tiemout': 1}),
            raises(ValidationError),
        )

    def test_unknown_key_alongside_valid_key_raises(self):
        assert_that(
            calling(_schema.load).with_args({'timeout': 1, 'unknown': 'value'}),
            raises(ValidationError),
        )
