# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo.status import Status
from xivo_bus.consumer import BusConsumer
from xivo_bus.publisher import BusPublisher


class CoreBus(BusPublisher, BusConsumer):
    def __init__(
        self,
        service_uuid,
        enabled=True,
        username='guest',
        password='guest',
        host='localhost',
        port=5672,
        exchange_name='',
        exchange_type='',
        **kwargs
    ):
        name = 'wazo-dird'
        super().__init__(
            name=name,
            service_uuid=service_uuid,
            username=username,
            password=password,
            host=host,
            port=port,
            exchange_name=exchange_name,
            exchange_type=exchange_type,
            **kwargs
        )
        self.enabled = enabled

    def provide_status(self, status):
        status['bus_consumer']['status'] = (
            Status.ok if self.consumer_connected() else Status.fail
        )

    def publish(self, event, extra_headers=None, payload=None):
        if not self.enabled:
            return
        super().publish(event, extra_headers, payload)

    def start(self):
        if not self.enabled:
            return
        super().start()
