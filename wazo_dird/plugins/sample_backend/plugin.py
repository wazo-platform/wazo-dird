# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.plugins.base_plugins import SourcePluginDependencies
from wazo_dird.plugins.source_result import _SourceResult as SourceResult

DESC = (
    'It works but this wazo-dird installation is still using the default configuration'
)
SAMPLE_RESULT = {
    'id': 1,
    'firstname': 'John',
    'lastname': 'Doe',
    'number': '555',
    'description': DESC,
}


class SamplePlugin(BaseSourcePlugin):
    def load(self, args: SourcePluginDependencies) -> None:
        self._config = args.get('config', {})
        self._name = self._config.get('name', 'sample_directory')
        self._format_columns = self._config.get('format_columns', {})

        backend = self._config.get('backend', '')
        result_class = make_result_class(
            backend, self._name, 'id', self._format_columns
        )
        self._result = result_class(SAMPLE_RESULT)

    def search(
        self, term: str, args: dict[str, Any] | None = None
    ) -> list[SourceResult]:
        return [self._result]

    def first_match(
        self, term: str, args: dict[str, Any] | None = None
    ) -> SourceResult | None:
        return self._result

    def match_all(
        self, extens: list[str], args: dict[str, Any] | None = None
    ) -> dict[str, SourceResult]:
        return {exten: self._result for exten in extens}
