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

import subprocess
import unittest
import requests
import os
import logging

from hamcrest import assert_that, equal_to

logger = logging.getLogger(__name__)


class BaseDirdIntegrationTest(unittest.TestCase):

    @classmethod
    def launch_dird_with_asset(cls):
        cls.container_name = cls.asset
        asset_path = os.path.join(os.path.dirname(__file__), '..', 'assets', cls.asset)
        cls.cur_dir = os.getcwd()
        os.chdir(asset_path)
        cls._run_cmd('docker-compose rm --force')
        cls._run_cmd('docker-compose run --rm sync')

    @classmethod
    def stop_dird_with_asset(cls):
        cls._run_cmd('docker-compose kill')
        os.chdir(cls.cur_dir)

    @staticmethod
    def _run_cmd(cmd):
        process = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = process.communicate()
        logger.info(out)

    @classmethod
    def setUpClass(cls):
        cls.launch_dird_with_asset()

    @classmethod
    def tearDownClass(cls):
        cls.stop_dird_with_asset()

    def get_lookup_result(self, term, profile, token=None):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}?term={term}'
        result = requests.get(url.format(profile=profile, term=term), headers={'X-Auth-Token': token})
        return result

    def lookup(self, term, profile):
        response = self.get_lookup_result(term, profile, token='valid-token')
        assert_that(response.status_code, equal_to(200))
        return response.json()

    def get_headers_result(self, profile, token=None):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}/headers'
        result = requests.get(url.format(profile=profile), headers={'X-Auth-Token': token})
        return result

    def headers(self, profile):
        response = self.get_headers_result(profile, token='valid-token')
        assert_that(response.status_code, equal_to(200))
        return response.json()

    def get_favorites_result(self, profile, token=None):
        url = 'http://localhost:9489/0.1/directories/favorites/{profile}'
        result = requests.get(url.format(profile=profile), headers={'X-Auth-Token': token})
        return result

    def favorites(self, profile):
        response = self.get_favorites_result(profile, token='valid-token')
        assert_that(response.status_code, equal_to(200))
        return response.json()

    def put_favorite_result(self, directory, contact, token=None):
        url = 'http://localhost:9489/0.1/directories/favorites/{directory}/{contact}'
        result = requests.put(url.format(directory=directory, contact=contact), headers={'X-Auth-Token': token})
        return result

    def put_favorite(self, directory, contact):
        response = self.put_favorite_result(directory, contact, token='valid-token')
        assert_that(response.status_code, equal_to(204))

    def delete_favorite_result(self, directory, contact, token=None):
        url = 'http://localhost:9489/0.1/directories/favorites/{directory}/{contact}'
        result = requests.delete(url.format(directory=directory, contact=contact), headers={'X-Auth-Token': token})
        return result

    def delete_favorite(self, directory, contact):
        response = self.delete_favorite_result(directory, contact, token='valid-token')
        assert_that(response.status_code, equal_to(204))
