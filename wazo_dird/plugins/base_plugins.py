# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import abc

from wazo_dird.plugins.source_result import _SourceResult as SourceResult


class BaseServicePlugin(metaclass=abc.ABCMeta):
    """
    This is the base class of a dird service. The service is responsible of
    its directory sources
    """

    @abc.abstractmethod
    def load(self, args):
        """
        Bootstraps the plugin instance. The flask app, bus connection and other
        handles will be passed through the args dictionary
        """

    def unload(self):
        """
        Does the cleanup before the service can be deleted
        """


class BaseViewPlugin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def load(self, dependencies):
        """
        The load method is responsible of acquiring resources for the plugin and
        add the routes to the http_app.
        """


class BaseSourcePlugin(metaclass=abc.ABCMeta):
    """
    A backend plugin in wazo should implement this base class implicitly or
    explicitly
    """

    # These string are expected in the configuration
    SEARCHED_COLUMNS = 'searched_columns'  # These columns are the ones we search in
    # These columns are the ones we search for reverse lookup
    FIRST_MATCHED_COLUMNS = 'first_matched_columns'
    FORMAT_COLUMNS = 'format_columns'
    UNIQUE_COLUMN = 'unique_column'  # This is the column that make an entry unique

    @abc.abstractmethod
    def load(self, args):
        """
        The load function is responsible for setting up the source and acquiring
        any resources necessary.
        """

    def unload(self):
        """
        The unload method is used to release any resources that are under the
        responsibility of this instance.
        """

    @abc.abstractmethod
    def search(self, term: str, args=None) -> list[SourceResult]:
        """
        The search method should return a list of dict containing the search
        results.

        The results should include the columns that are expected by the display.
        When columns from the source do not match the columns from the display,
        the `format_columns` dictionary can be used by the administrator
        to add or modify columns.

        If the backend has a `unique_column` configuration, a new column will be
        added with a `__unique_id` header containing the unique key.
        """

    @abc.abstractmethod
    def first_match(self, exten: str, args=None) -> SourceResult | None:
        """
        The first_match method should return a dict containing the first matched
        result.

        The results should include the columns that are expected by the display.
        When columns from the source do not match the columns from the display,
        the `format_columns` dictionary can be used by the administrator
        to add or modify columns.

        If the backend has a `unique_column` configuration, a new column will be
        added with a `__unique_id` header containing the unique key.
        """

    def match_all(self, extens: list[str], args=None) -> dict[str, SourceResult]:
        """
        The match_all method should return a dict with exten matched as key and
        a dict containing result as value.

        The results should include the columns that are expected by the display.
        When columns from the source do not match the columns from the display,
        the `format_columns` dictionary can be used by the administrator
        to add or modify columns.

        If the backend has a `unique_column` configuration, a new column will be
        added with a `__unique_id` header containing the unique key.
        """
        results = {}
        for exten in extens:
            entry = self.first_match(exten, args=args)
            if entry:
                results[exten] = entry
        return results

    def list(self, uids: list[str], args) -> list[SourceResult]:
        """
        Returns a list of results based on the unique column for this backend.
        This function is not mandatory as some backends make it harder than
        others to query for specific ids. If a backend does not provide the list
        function, it will not be possible to set a favourite from this backend.

        Results returned from list should be formatted in the same way than
        results from search. Meaning that the `__unique_id` column should be
        added and display columns should be present.
        """
        return []
