# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import (
    all_of,
    assert_that,
    calling,
    empty,
    has_entries,
    instance_of,
    not_,
    raises,
)

from marshmallow.exceptions import ValidationError

from ..schemas import source_schema


class TestSourceSchema(TestCase):
    def setUp(self):
        self._name = 'my_wazo_source'
        self._body = {'name': self._name}

    def test_post_minimal_body(self):
        body = dict(auth={'username': 'foo', 'password': 'bar'}, **self._body)

        parsed = source_schema.load(body)
        assert_that(
            parsed,
            has_entries(
                name=self._name,
                first_matched_columns=empty(),
                searched_columns=empty(),
                format_columns=all_of(instance_of(dict), empty()),
                auth=has_entries(
                    host='localhost',
                    port=9497,
                    username='foo',
                    password='bar',
                    prefix='/api/auth',
                    https=True,
                    verify_certificate=True,
                ),
                confd=has_entries(
                    host='localhost',
                    port=9486,
                    prefix='/api/confd',
                    https=True,
                    verify_certificate=True,
                ),
            ),
        )

    def test_that_username_password_or_keyfile_is_present(self):
        username_password = {'username': 'foo', 'password': 'bar'}
        key_file = {
            'key_file': '/var/lib/wazo-auth-keys/wazo-dird-wazo-backend-key.yml'
        }
        username_and_key_file = {'username': 'foo', 'key_file': 'bar'}
        no_auth_info = {}

        assert_that(
            calling(source_schema.load).with_args(
                dict(auth=username_password, **self._body)
            ),
            not_(raises(Exception)),
        )

        assert_that(
            calling(source_schema.load).with_args(dict(auth=key_file, **self._body)),
            not_(raises(Exception)),
        )

        assert_that(
            calling(source_schema.load).with_args(
                dict(auth=no_auth_info, **self._body)
            ),
            raises(ValidationError),
        )

        assert_that(
            calling(source_schema.load).with_args(
                dict(auth=username_and_key_file, **self._body)
            ),
            raises(ValidationError),
        )

    def test_verify_certificate(self):
        cert_filename = '/usr/share/xivo-certs/server.crt'
        verify_true = {'verify_certificate': True, 'key_file': '/not/important'}
        verify_false = {'verify_certificate': False, 'key_file': '/not/important'}
        verify_file = {
            'verify_certificate': cert_filename,
            'key_file': '/not/important',
        }

        body = dict(auth=verify_true, confd=verify_true, **self._body)
        parsed = source_schema.load(body)
        assert_that(
            parsed,
            has_entries(
                auth=has_entries(verify_certificate=True),
                confd=has_entries(verify_certificate=True),
            ),
        )

        body = dict(auth=verify_false, confd=verify_false, **self._body)
        parsed = source_schema.load(body)
        assert_that(
            parsed,
            has_entries(
                auth=has_entries(verify_certificate=False),
                confd=has_entries(verify_certificate=False),
            ),
        )

        body = dict(auth=verify_file, confd=verify_file, **self._body)
        parsed = source_schema.load(body)
        assert_that(
            parsed,
            has_entries(
                auth=has_entries(verify_certificate=cert_filename),
                confd=has_entries(verify_certificate=cert_filename),
            ),
        )
