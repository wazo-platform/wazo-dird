# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Give the suite the shared asset plugin of wazo_test_helpers.

The plugin groups the test classes by the asset they ask for, starts each stack
once, and stops it as soon as the next class needs another one. A test class
asks for its stack with `asset = '<name>'`; see `suite/helpers/base.py`.

One fixture is built for each asset class, because the marker that the plugin
reads is the name of the fixture.
"""
from __future__ import annotations

import pytest
from suite.helpers import base
from wazo_test_helpers.pytest_asset import asset_fixture, register


def pytest_configure(config: pytest.Config) -> None:
    register(config)


for _name, _asset_class in base.ASSET_CLASSES.items():
    globals()[_name] = asset_fixture(_asset_class)

# `enable_mark_logs_fixture` is not enabled: it marks the logs of `cls.service`,
# and the backend assets never start a dird container - their `sync` waits for
# the mock alone - so it raises NoSuchService on each of their tests. The fixture
# is autouse and every test file sits in this one directory, so a narrower
# conftest cannot exclude them either.
