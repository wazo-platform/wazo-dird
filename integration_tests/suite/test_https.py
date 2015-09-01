# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import time

from hamcrest import assert_that
from hamcrest import contains_string
from .base_dird_integration_test import BaseDirdIntegrationTest


class TestHTTPSMissingCertificate(BaseDirdIntegrationTest):
    asset = 'no-ssl-certificate'

    def test_given_inexisting_SSL_certificate_when_dird_starts_then_dird_stops(self):
        for _ in range(5):
            status = self.dird_status()[0]
            if not status['State']['Running']:
                break
            time.sleep(1)
        else:
            self.fail('xivo-dird did not stop while missing SSL certificate')

        log = self.dird_logs()
        assert_that(log, contains_string("No such file or directory: '/etc/ssl/server.crt'"))


class TestHTTPSMissingPrivateKey(BaseDirdIntegrationTest):
    asset = 'no-ssl-private-key'

    def test_given_inexisting_SSL_private_key_when_dird_starts_then_dird_stops(self):
        for _ in range(2):
            status = self.dird_status()[0]
            if not status['State']['Running']:
                break
            time.sleep(1)
        else:
            self.fail('xivo-dird did not stop while missing SSL private key')

        log = self.dird_logs()
        assert_that(log, contains_string("No such file or directory: '/etc/ssl/server.key'"))
