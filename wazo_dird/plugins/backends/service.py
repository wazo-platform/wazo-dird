# Copyright 2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+


class BackendService:

    def __init__(self, config):
        self._configured_backends = []
        for backend_name, enabled in config['enabled_plugins']['backends'].items():
            if not enabled:
                continue
            backend = {'name': backend_name}
            self._configured_backends.append(backend)

    def list_(self):
        return self._configured_backends

    def count(self):
        return len(self._configured_backends)
