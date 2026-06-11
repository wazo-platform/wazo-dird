# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock, patch

from ..plugin import _ReverseService

_PROFILE_NO_TIMEOUT = {
    'name': 'test',
    'services': {'reverse': {'sources': []}},
}

_PROFILE_WITH_TIMEOUT = {
    'name': 'test',
    'services': {'reverse': {'sources': [], 'timeout': 0.5}},
}


def _make_service() -> _ReverseService:
    source_manager = Mock()
    source_manager.get.return_value = None
    return _ReverseService(config={}, source_manager=source_manager, controller=Mock())


class TestReverseTimeout(unittest.TestCase):
    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_default_timeout(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse(_PROFILE_NO_TIMEOUT, '1234', 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_explicit_timeout_overrides_default(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse(_PROFILE_WITH_TIMEOUT, '1234', 'test')

        mock_as_completed.assert_called_once_with([], timeout=0.5)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_default_timeout(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse_many(_PROFILE_NO_TIMEOUT, ['1234'], 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_explicit_timeout_overrides_default(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse_many(_PROFILE_WITH_TIMEOUT, ['1234'], 'test')

        mock_as_completed.assert_called_once_with([], timeout=0.5)
