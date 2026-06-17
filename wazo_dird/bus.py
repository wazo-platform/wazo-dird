# Copyright 2016-2024 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Any

from wazo_bus.consumer import BusConsumer
from wazo_bus.publisher import BusPublisher
from wazo_bus.resources.common.abstract import EventProtocol
from xivo.status import Status, StatusDict


class CoreBus(BusPublisher, BusConsumer):  # type: ignore[misc]
    def __init__(
        self,
        service_uuid: str | None,
        enabled: bool = True,
        username: str = 'guest',
        password: str = 'guest',
        host: str = 'localhost',
        port: int = 5672,
        exchange_name: str = '',
        exchange_type: str = '',
        **kwargs: Any,
    ) -> None:
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
            **kwargs,
        )
        self.enabled = enabled

    def provide_status(self, status: StatusDict) -> None:
        status['bus_consumer']['status'] = (
            Status.ok if self.consumer_connected() else Status.fail
        )

    def publish(
        self,
        event: EventProtocol,
        extra_headers: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        super().publish(event, extra_headers, payload)

    def start(self) -> None:
        if not self.enabled:
            return
        super().start()
