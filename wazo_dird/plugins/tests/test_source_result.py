# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    is_,
    none,
)
from mock import sentinel
from wazo_dird.plugins.source_result import (
    _NoErrorFormatter as Formatter,
    _SourceResult,
    make_result_class,
)


class TestSourceResult(unittest.TestCase):

    def setUp(self):
        self.xivo_id = sentinel.xivo_id
        self.fields = {
            'client_no': 1,
            'firstname': 'fn',
            'lastname': 'ln',
            'list': [{'foo': 'bar'}, None],
        }
        self.empty_relations = {
            'xivo_id': self.xivo_id,
            'agent_id': None,
            'user_id': None,
            'user_uuid': None,
            'endpoint_id': None,
            'source_entry_id': None,
        }

    def test_source(self):
        r = _SourceResult(self.fields, self.xivo_id)
        r.source = sentinel.source

        assert_that(r.source, equal_to(sentinel.source))

    def test_fields(self):
        r = _SourceResult(self.fields, self.xivo_id)

        assert_that(r.fields, equal_to(self.fields))
        assert_that(r.relations, equal_to(self.empty_relations))

    def test_agent_relation(self):
        r = _SourceResult(self.fields, self.xivo_id, agent_id=sentinel.agent_id)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': sentinel.agent_id,
                                           'user_id': None,
                                           'user_uuid': None,
                                           'endpoint_id': None,
                                           'source_entry_id': None}))

    def test_user_relation(self):
        r = _SourceResult(self.fields, sentinel.xivo_id,
                          user_id=sentinel.user_id, user_uuid=sentinel.user_uuid)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': None,
                                           'user_id': sentinel.user_id,
                                           'user_uuid': sentinel.user_uuid,
                                           'endpoint_id': None,
                                           'source_entry_id': None}))

    def test_endpoint_relation(self):
        r = _SourceResult(self.fields, sentinel.xivo_id, endpoint_id=sentinel.endpoint_id)

        assert_that(r.relations, equal_to({'xivo_id': sentinel.xivo_id,
                                           'agent_id': None,
                                           'user_id': None,
                                           'user_uuid': None,
                                           'endpoint_id': sentinel.endpoint_id,
                                           'source_entry_id': None}))

    def test_get_unique(self):
        r = _SourceResult(self.fields)
        r._unique_column = 'client_no'

        assert_that(r.get_unique(), equal_to('1'))

    def test_that_format_columns_transformation_are_applied(self):
        SourceResult = make_result_class(
            sentinel.name,
            format_columns={
                'fn': '{firstname}',
                'ln': '{lastname}',
                'name': '{firstname} {lastname}',
                'simple_error': '{missing}',
                'complex_error': '{missing[0][field]}',
                'super_complex_error': '{list[0][missing]}',
                'crazy_error': '{list[1][missing]}',
            }
        )

        r = SourceResult(self.fields)

        assert_that(r.fields, has_entries(
            fn='fn',
            ln='ln',
            name='fn ln',
            simple_error=None,
            complex_error=None,
            super_complex_error=None,
            crazy_error=None,
        ))

    def test_that_the_source_entry_id_is_added_to_relations(self):
        SourceResult = make_result_class('foobar', unique_column='email')

        r = SourceResult({'fn': 'Foo',
                          'ln': 'Bar',
                          'email': 'foobar@example.com'})

        assert_that(r.relations['source_entry_id'], equal_to('foobar@example.com'))


class TestMakeResultClass(unittest.TestCase):

    def test_source_name(self):
        SourceResult = make_result_class(sentinel.source_name)

        s = SourceResult({})

        assert_that(s.source, equal_to(sentinel.source_name))

    def test_source_unique_column(self):
        SourceResult = make_result_class(sentinel.source_name, 'the-unique-column')

        s = SourceResult({})

        assert_that(s._unique_column, equal_to('the-unique-column'))
        assert_that(s._format_columns, equal_to({}))

    def test_format_columns(self):
        SourceResult = make_result_class(sentinel.source_name,
                                         format_columns={'to': '{from}'})

        s = SourceResult({})

        assert_that(s._format_columns, equal_to({'to': '{from}'}))
        assert_that(s._unique_column, none())

    def test_deletable(self):
        SourceResult = make_result_class(sentinel.source_name,
                                         is_deletable=True)

        s = SourceResult({})

        assert_that(s.is_deletable, is_(True))


class TestFormatter(unittest.TestCase):

    def setUp(self):
        self.formatter = Formatter()

    def test_that_missing_keys_do_not_raise_an_exception(self):
        result = self.formatter.format('{missing}', **{'foo': 'bar'})

        assert_that(result, equal_to(''))

    def test_that_a_missing_key_in_a_string_combining_two_fields(self):
        result = self.formatter.format('{firstname} {lastname}', **{'firstname': 'Alice'})

        assert_that(result, equal_to('Alice'))

    def test_that_a_None_value_is_not_replaced_by_the_None_string(self):
        result = self.formatter.format('{mobile}', **{'mobile': None})

        assert_that(result, is_(''))
