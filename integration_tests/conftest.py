# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from collections.abc import Iterator

import pytest
from suite.helpers import base
from wazo_test_helpers.asset_launching_test_case import NoSuchService
from wazo_test_helpers.pytest_asset import asset_fixture, register


def pytest_configure(config: pytest.Config) -> None:
    register(config)


for _name, _asset_class in base.ASSET_CLASSES.items():
    globals()[_name] = asset_fixture(_asset_class)


@pytest.fixture(autouse=True, scope='function')
def mark_logs(request: pytest.FixtureRequest) -> Iterator[None]:
    """Bracket each test in the logs of its `dird` container.

    A few assets (`database`, `wazo_confd`, the `csv_ws_*` mocks) test a
    backend directly and never start a `dird` container, so marking their
    logs raises `NoSuchService`; skip those instead of failing the test.
    """
    cls = request.cls
    if cls is None or not hasattr(cls, 'asset_cls'):
        yield
        return
    test_name = f'{cls.__name__}.{request.function.__name__}'
    try:
        cls.asset_cls.mark_logs_test_start(test_name)
    except NoSuchService:
        yield
        return
    yield
    cls.asset_cls.mark_logs_test_end(test_name)
