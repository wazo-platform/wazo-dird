# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from pkg_resources import iter_entry_points


class BackendService:

    backend_entry_points = 'wazo_dird.backends'

    def __init__(self, config):
        configured_backends = set()
        for backend_name, enabled in config['enabled_plugins']['backends'].items():
            if not enabled:
                continue
            configured_backends.add(backend_name)

        installed_backends = set()
        for module in iter_entry_points(group=self.backend_entry_points):
            backend_name = str(module).split(' = ', 1)[0]
            installed_backends.add(backend_name)

        self._backends = [{'name': backend} for backend in configured_backends & installed_backends]

    def list_(self):
        return self._backends

    def count(self):
        return len(self._backends)
