# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from time import time

from wazo_dird.auth import required_acl
from wazo_dird.rest_api import AuthResource

logger = logging.getLogger(__name__)


class Headers(AuthResource):
    displays = None

    @classmethod
    def configure(cls, displays):
        cls.displays = displays

    @required_acl('dird.directories.lookup.{profile}.headers.read')
    def get(self, profile):
        logger.debug('header request on profile %s', profile)
        if profile not in self.displays:
            logger.warning(
                'profile %s does not exist, or associated display does not exist',
                profile
            )
            error = {
                'reason': ['The profile `{profile}` does not exist'.format(profile=profile)],
                'timestamp': [time()],
                'status_code': 404,
            }
            return error, 404

        display = self.displays[profile]
        response = format_headers(display)
        return response


def format_headers(display):
    return {
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
    }
