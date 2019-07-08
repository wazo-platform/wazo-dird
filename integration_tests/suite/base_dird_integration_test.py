# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import logging
import requests

from stevedore import DriverManager

from .helpers.constants import ASSET_ROOT

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()


def absolute_file_name(asset_name, path):
    dirname, basename = os.path.split(path)
    real_basename = 'asset.{}.{}'.format(asset_name, basename)
    return os.path.join(ASSET_ROOT, dirname, real_basename)


class BackendWrapper:

    def __init__(self, backend, dependencies):
        manager = DriverManager(
            namespace='wazo_dird.backends',
            name=backend,
            invoke_on_load=True,
        )
        self._source = manager.driver
        self._source.load(dependencies)

    def unload(self):
        self._source.unload()

    def search(self, term, *args, **kwargs):
        return [r.fields for r in self.search_raw(term, *args, **kwargs)]

    def search_raw(self, term, *args, **kwargs):
        return self._source.search(term, *args, **kwargs)

    def first(self, term, *args, **kwargs):
        return self._source.first_match(term, *args, **kwargs).fields

    def list(self, source_ids, *args, **kwargs):
        results = self._source.list(source_ids, *args, **kwargs)
        return [r.fields for r in results]
