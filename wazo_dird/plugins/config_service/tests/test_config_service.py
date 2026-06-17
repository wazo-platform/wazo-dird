# Copyright 2016-2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock
from unittest.mock import sentinel as s

from hamcrest import assert_that, equal_to, has_entries

from ..plugin import Service


class TestConfigService(unittest.TestCase):
    def test_that_get_config_returns_the_config(self):
        service = Service(s.original_config, Mock(), s.controller, None, None)

        config = service.get_config()

        assert_that(config, equal_to(s.original_config))


class TestAutoCreateProfile(unittest.TestCase):
    def _make_service(self):
        controller = Mock()
        service = Service(
            config={},
            bus=Mock(),
            controller=controller,
            tenant_crud=Mock(),
            confd_client=Mock(),
        )
        return service, controller

    def test_auto_create_profile_puts_reverse_timeout_under_options(self):
        service, controller = self._make_service()
        profile_service = Mock()
        controller.services.get.return_value = profile_service

        service._auto_create_profile(
            tenant_uuid='tenant-uuid',
            name='mytenant',
            display={'uuid': 'display-uuid'},
            sources=[{'uuid': 'source-uuid'}],
        )

        (_, kwargs) = profile_service.create.call_args
        reverse_config = kwargs['services']['reverse']
        assert_that(
            reverse_config,
            has_entries(options=has_entries(timeout=0.5)),
        )
