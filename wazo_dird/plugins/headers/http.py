# Copyright 2014-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging

from wazo_dird.exception import OldAPIException
from wazo_dird.helpers import DisplayAwareResource
from wazo_dird.auth import required_acl
from wazo_dird.rest_api import LegacyAuthResource

logger = logging.getLogger(__name__)


class Headers(LegacyAuthResource, DisplayAwareResource):

    def __init__(self, display_service, profile_to_display):
        self.display_service = display_service
        self.profile_to_display = profile_to_display

    @required_acl('dird.directories.lookup.{profile}.headers.read')
    def get(self, profile):
        logger.debug('header request on profile %s', profile)
        try:
            display = self.build_display(profile)
        except OldAPIException as e:
            return e.body, e.status_code
        response = format_headers(display)
        return response


def format_headers(display):
    return {
        'column_headers': [d.title for d in display],
        'column_types': [d.type for d in display],
    }
