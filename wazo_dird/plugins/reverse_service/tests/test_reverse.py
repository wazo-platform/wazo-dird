# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock, patch

from ..plugin import _ReverseService

_SOURCE_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

_PROFILE_NO_TIMEOUT = {
    'name': 'test',
    'services': {'reverse': {'sources': []}},
}

_PROFILE_WITH_SOURCE = {
    'name': 'test',
    'services': {'reverse': {'sources': [{'uuid': _SOURCE_UUID}]}},
}

_PROFILE_WITH_TIMEOUT = {
    'name': 'test',
    'services': {'reverse': {'sources': [], 'options': {'timeout': 0.5}}},
}

# timeout outside options is stripped by the profile schema (EXCLUDE unknown fields)
_PROFILE_WITH_TOPLEVEL_TIMEOUT = {
    'name': 'test',
    'services': {'reverse': {'sources': [], 'timeout': 0.5}},
}


def _make_service() -> _ReverseService:
    source_manager = Mock()
    source_manager.get.return_value = None
    return _ReverseService(config={}, source_manager=source_manager, controller=Mock())


def _make_service_with_source() -> tuple[_ReverseService, Mock]:
    source = Mock()
    source_manager = Mock()
    source_manager.get.return_value = source
    service = _ReverseService(
        config={}, source_manager=source_manager, controller=Mock()
    )
    return service, source


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

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_toplevel_timeout_is_ignored(self, mock_as_completed):
        # timeout not nested under options is stripped by the profile API schema;
        # the service must fall back to the default rather than silently using it
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse(_PROFILE_WITH_TOPLEVEL_TIMEOUT, '1234', 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_toplevel_timeout_is_ignored(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse_many(_PROFILE_WITH_TOPLEVEL_TIMEOUT, ['1234'], 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_cancels_pending_on_timeout(self, mock_as_completed):
        mock_as_completed.side_effect = TimeoutError
        future = Mock()
        future.done.return_value = False
        service, _ = _make_service_with_source()
        service._executor.submit = Mock(return_value=future)

        service.reverse(_PROFILE_WITH_SOURCE, '1234', 'test')

        future.cancel.assert_called_once()

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_cancels_pending_on_timeout(self, mock_as_completed):
        mock_as_completed.side_effect = TimeoutError
        future = Mock()
        future.done.return_value = False
        service, _ = _make_service_with_source()
        service._executor.submit = Mock(return_value=future)

        service.reverse_many(_PROFILE_WITH_SOURCE, ['1234'], 'test')

        future.cancel.assert_called_once()
