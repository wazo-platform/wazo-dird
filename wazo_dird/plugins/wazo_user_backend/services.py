# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

logger = logging.getLogger(__name__)


class WazoBackendService:

    def __init__(self, source_crud):
        self._source_crud = source_crud

    def create(self, **body):
        return self._source_crud.create(body)
