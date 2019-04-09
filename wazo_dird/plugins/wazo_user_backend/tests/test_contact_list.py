# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from hamcrest import (
    assert_that,
    equal_to,
)
from mock import (
    Mock,
    sentinel as s,
)

from ..contact import ContactLister


class TestContactLister(TestCase):

    def setUp(self):
        self.client = Mock()

        self.lister = ContactLister(self.client)

    def test_pagination(self):
        result = self.lister.list(limit=2, offset=42)

        assert_that(result, equal_to(self.client.users.list.return_value))
        self.client.users.list.assert_called_once_with(view='directory', limit=2, offset=42)

    def test_search(self):
        result = self.lister.list(search='foo', firstname='john')

        assert_that(result, equal_to(self.client.users.list.return_value))
        self.client.users.list.assert_called_once_with(
            view='directory',
            search='foo',
            firstname='john',
        )
