# Copyright 2020-2022 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_test_helpers.bus import BusClient
from wazo_test_helpers import until
from hamcrest import assert_that, has_item, has_entries, has_entry

from .helpers.base import BaseDirdIntegrationTest


class TestBusConsumer(BaseDirdIntegrationTest):

    asset = 'all_routes'

    def setUp(self):
        super().setUp()
        until.true(self.bus_is_up, tries=10)
        bus_port = self.service_port(5672, 'rabbitmq')
        self.bus = BusClient.from_connection_fields(
            host='127.0.0.1',
            port=bus_port,
            exchange_name='wazo-headers',
            exchange_type='headers',
        )

    def test_message_is_received(self):
        bus_events = self.bus.accumulator(headers={'name': 'dird_pong'})

        ping_event = {'name': 'dird_ping', 'data': {'payload': 'ping'}}

        self.bus.publish(
            ping_event,
            headers={'name': 'dird_ping'},
            routing_key='dird.test',
        )

        def pong_bus_event_received():
            assert_that(
                bus_events.accumulate(with_headers=True),
                has_item(
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                payload='pong',
                            ),
                        ),
                        headers=has_entry('name', 'dird_pong'),
                    )
                ),
            )

        until.assert_(pong_bus_event_received, tries=5)

    def test_message_is_received_after_error(self):
        bus_events = self.bus.accumulator(headers={'name': 'dird_pong'})

        crash_event = {'name': 'crash_ping', 'data': {'payload': 'ping'}}
        self.bus.publish(
            crash_event,
            headers={'name': 'crash_ping'},
            routing_key='dird.test',
        )

        ping_event = {'name': 'dird_ping', 'data': {'payload': 'ping'}}
        self.bus.publish(
            ping_event,
            headers={'name': 'dird_ping'},
            routing_key='dird.test',
        )

        def pong_bus_event_received():
            assert_that(
                bus_events.accumulate(with_headers=True),
                has_item(
                    has_entries(
                        message=has_entries(
                            data=has_entries(
                                payload='pong',
                            ),
                        ),
                        headers=has_entry('name', 'dird_pong'),
                    )
                ),
            )

        until.assert_(pong_bus_event_received, tries=5)
