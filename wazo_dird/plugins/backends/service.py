# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from pkg_resources import iter_entry_points


class BackendService:

    _backend_entry_points = 'wazo_dird.backends'
    _searchable_fields = ['name']

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

    def list_(self, search=None, **kwargs):
        matches = []

        for backend in self._backends:
            if search is None:
                matches.append(backend)
                continue
            for field in self._searchable_fields:
                value = backend.get(field)
                if search in value:
                    matches.append(backend)
                    break

        return matches

    def count(self, search=None, **kwargs):
        return len(self.list_(search))
