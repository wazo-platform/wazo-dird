# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from typing import cast
from unittest.mock import Mock, patch

from wazo_dird.helpers import ProfileConfig

from ..plugin import _ReverseService

_SOURCE_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'

_PROFILE_NO_TIMEOUT = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': []}},
    },
)

_PROFILE_WITH_SOURCE = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': [{'uuid': _SOURCE_UUID}]}},
    },
)

_PROFILE_WITH_TIMEOUT = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': [], 'options': {'timeout': 0.5}}},
    },
)

# timeout outside options is rejected by the profile schema (RAISE on unknown fields)
_PROFILE_WITH_TOPLEVEL_TIMEOUT = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': [], 'timeout': 0.5}},
    },
)

_PROFILE_WITH_NULL_OPTIONS = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': [], 'options': None}},
    },
)

_PROFILE_WITH_ZERO_TIMEOUT = cast(
    ProfileConfig,
    {
        'name': 'test',
        'services': {'reverse': {'sources': [], 'options': {'timeout': 0}}},
    },
)


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
    def test_reverse_null_options_uses_default_timeout(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse(_PROFILE_WITH_NULL_OPTIONS, '1234', 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_null_options_uses_default_timeout(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse_many(_PROFILE_WITH_NULL_OPTIONS, ['1234'], 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_zero_timeout_uses_default(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse(_PROFILE_WITH_ZERO_TIMEOUT, '1234', 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_zero_timeout_uses_default(self, mock_as_completed):
        mock_as_completed.return_value = iter([])
        service = _make_service()

        service.reverse_many(_PROFILE_WITH_ZERO_TIMEOUT, ['1234'], 'test')

        mock_as_completed.assert_called_once_with([], timeout=1)

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_cancels_pending_on_timeout(self, mock_as_completed):
        mock_as_completed.side_effect = TimeoutError
        future = Mock()
        future.done.return_value = False
        service, _ = _make_service_with_source()
        setattr(service._executor, 'submit', Mock(return_value=future))

        service.reverse(_PROFILE_WITH_SOURCE, '1234', 'test')

        future.cancel.assert_called_once()

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_cancels_pending_on_timeout(self, mock_as_completed):
        mock_as_completed.side_effect = TimeoutError
        future = Mock()
        future.done.return_value = False
        service, _ = _make_service_with_source()
        setattr(service._executor, 'submit', Mock(return_value=future))

        service.reverse_many(_PROFILE_WITH_SOURCE, ['1234'], 'test')

        future.cancel.assert_called_once()

    @patch('wazo_dird.plugins.reverse_service.plugin.as_completed')
    def test_reverse_many_keeps_first_match_when_sources_disagree(
        self, mock_as_completed
    ):
        # a later-completing source must not overwrite an exten already
        # matched by an earlier one, matching reverse()'s first-match-wins
        exten_a, exten_b = '1111', '2222'
        match_a1, match_a2, match_b = Mock(), Mock(), Mock()

        first_future = Mock()
        first_future.result.return_value = {exten_a: match_a1}
        first_future.done.return_value = True

        second_future = Mock()
        second_future.result.return_value = {exten_a: match_a2, exten_b: match_b}
        second_future.done.return_value = True

        mock_as_completed.return_value = iter([first_future, second_future])
        service, _ = _make_service_with_source()
        setattr(service._executor, 'submit', Mock(return_value=Mock()))

        results = service.reverse_many(_PROFILE_WITH_SOURCE, [exten_a, exten_b], 'test')

        assert results == [match_a1, match_b]
