# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from operator import itemgetter
from pkg_resources import iter_entry_points


class BackendService:

    _backend_entry_points = 'wazo_dird.backends'

    def __init__(self, config):
        configured_backends = set()
        for backend_name, enabled in config['enabled_plugins']['backends'].items():
            if not enabled:
                continue
            configured_backends.add(backend_name)

        installed_backends = set()
        for module in iter_entry_points(group=self._backend_entry_points):
            backend_name = str(module).split(' = ', 1)[0]
            installed_backends.add(backend_name)

        self._backends = [{'name': backend} for backend in configured_backends & installed_backends]

    def list_(self, **kwargs):
        matches = self._filter_matches(self._backends, **kwargs)
        filtered = self._sort(matches, **kwargs)
        paginated = self._paginate(filtered, **kwargs)
        return paginated

    def count(self, **kwargs):
        return len(self._filter_matches(self._backends, **kwargs))

    @staticmethod
    def _filter_matches(backends, search=None, **kwargs):
        searchable_fields = ['name']
        matchers = []

        if search is not None:
            for field in searchable_fields:
                matchers.append(lambda backend: search in backend[field])

        for field in searchable_fields:
            if field not in kwargs:
                continue
            matchers.append(lambda backend: kwargs[field] == backend[field])

        if not matchers:
            return backends

        matches = []

        for backend in backends:
            for matcher in matchers:
                if matcher(backend):
                    matches.append(backend)
                    continue

        return matches

    @staticmethod
    def _paginate(backends, limit=None, offset=None, **ignored):
        offset = 0 or offset

        if limit is not None:
            return backends[offset:limit+offset]

        return backends[offset:]

    @staticmethod
    def _sort(backends, order=None, direction=None, **ignored):
        reverse = direction == 'desc'
        return sorted(backends, key=itemgetter(order), reverse=reverse)
