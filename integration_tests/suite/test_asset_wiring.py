# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that each test class asks the asset plugin for the right stack.

These need no container. They guard the wiring of `base.DirdAssetRunningTestCase`
against a silent mistake: pytest gathers `pytestmark` along the whole MRO and the
plugin keeps the first marker it finds, so a marker on a base class would send
every subclass to the stack of that base class.
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

from .helpers import base


def _collected_subclasses() -> list[type[base.DirdAssetRunningTestCase]]:
    """Every class that pytest collects, that is every one named `Test*`.

    Import the whole suite first: this module comes early in the alphabet, so
    most of the test classes would not exist yet.
    """
    suite = importlib.import_module(__package__)
    for module in pkgutil.iter_modules(suite.__path__):
        if module.name.startswith('test_'):
            importlib.import_module(f'{__package__}.{module.name}')

    def walk(cls):
        for sub in cls.__subclasses__():
            yield sub
            yield from walk(sub)

    return [
        cls
        for cls in walk(base.DirdAssetRunningTestCase)
        if cls.__name__.startswith('Test')
    ]


def _own_usefixtures(cls: type) -> list[str]:
    """The markers that `cls` itself declares, not the ones it inherits."""
    return [
        str(mark.args[0])
        for mark in cls.__dict__.get('pytestmark', [])
        if mark.name == 'usefixtures' and mark.args
    ]


def _marked_ancestors(cls: type) -> list[type]:
    return [ancestor for ancestor in cls.__mro__ if _own_usefixtures(ancestor)]


def test_every_asset_has_a_compose_file() -> None:
    # A name with no override file builds a fixture that cannot start, and the
    # failure would only appear when a test asks for that fixture.
    overrides = {
        path.name.removeprefix('docker-compose.').removesuffix('.override.yml')
        for path in Path(base.ASSET_ROOT).glob('docker-compose.*.override.yml')
    }
    assert set(base.ASSET_CLASSES) - overrides == set()


def test_every_asset_class_is_registered_once() -> None:
    # `ASSET_CLASSES` is keyed by `asset`, so two classes that name the same
    # asset would silently leave one of them out, and its fixture with it.
    subclasses = base.DirdAssetLaunchingTestCase.__subclasses__()
    assert len(base.ASSET_CLASSES) == len(subclasses)
    for name, asset_class in base.ASSET_CLASSES.items():
        assert asset_class.asset == name
        assert asset_class.service == 'dird'
        # A stack holder that pytest collects would run as an empty test class.
        assert asset_class.__test__ is False


def test_collected_classes_ask_for_the_asset_they_declare() -> None:
    wrong = {
        f'{cls.__module__}.{cls.__name__}': (
            getattr(cls, 'asset', None),
            _own_usefixtures(cls),
        )
        for cls in _collected_subclasses()
        if _own_usefixtures(cls) != [getattr(cls, 'asset', None)]
    }
    assert not wrong, f'these classes would use the wrong stack: {wrong}'


def test_only_the_collected_class_of_a_chain_carries_a_marker() -> None:
    # pytest gathers `pytestmark` along the MRO and the plugin keeps the first
    # marker, so a second marked class in a chain would decide for the others.
    several = {
        f'{cls.__module__}.{cls.__name__}': [c.__name__ for c in _marked_ancestors(cls)]
        for cls in _collected_subclasses()
        if len(_marked_ancestors(cls)) != 1
    }
    assert not several, f'more than one marker in the chain of: {several}'


def test_an_unknown_asset_is_refused() -> None:
    with pytest.raises(RuntimeError, match='unknown asset'):

        class TestWithATypo(base.DirdAssetRunningTestCase):
            asset = 'ths_asset_does_not_exist'
