# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from uuid import uuid4

logger = logging.getLogger(__name__)


class WazoBackendService:

    def create(self, **kwargs):
        logger.critical('New wazo source: %s', kwargs)
        kwargs['uuid'] = str(uuid4())
        return kwargs
