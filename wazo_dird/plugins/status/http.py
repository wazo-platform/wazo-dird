# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.status import StatusAggregator, StatusDict

from wazo_dird.auth import required_acl
from wazo_dird.http import AuthResource


class StatusResource(AuthResource):
    def __init__(self, status_aggregator: StatusAggregator) -> None:
        self.status_aggregator = status_aggregator

    @required_acl('dird.status.read')
    def get(self) -> tuple[StatusDict, int]:
        return self.status_aggregator.status(), 200
