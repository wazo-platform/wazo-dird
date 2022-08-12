# Copyright 2020-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xivo_bus.resources.common.event import ServiceEvent


class PongEvent(ServiceEvent):
    name = 'dird_pong'
    routing_key_fmt = 'dird.test'

    def __init__(self):
        super().__init__({'payload': 'pong'})


class BrokenBusPlugin:
    def _bus_subscribe(self):
        self._bus.subscribe('dird_ping', self._on_ping)
        self._bus.subscribe('crash_ping', self._on_crash_ping)

    def load(self, dependencies):
        self._bus = dependencies['bus']
        self._bus_subscribe()

    def _on_ping(self, _):
        event = PongEvent()
        self._bus.publish(event)

    def _on_crash_ping(self, _):
        raise Exception('Crash message received')
