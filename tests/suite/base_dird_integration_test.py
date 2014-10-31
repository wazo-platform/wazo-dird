# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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
import json
import os
import time


class BaseDirdIntegrationTest(unittest.TestCase):

    @classmethod
    def launch_dird_with_asset(cls):
        asset_path = os.path.abspath(os.path.curdir) + '/tests/assets/%s' % cls.asset
        volumes = '%s:/etc/xivo/xivo-dird' % asset_path
        cmd = ['docker', 'run', '--name', __name__,
               '-v', volumes,
               '-d', '-p', '9489:9489', 'dird-test']
        subprocess.call(cmd)
        time.sleep(0.5)

    @classmethod
    def stop_dird_with_asset(cls):
        subprocess.call(['docker', 'kill', __name__])
        subprocess.call(['docker', 'rm', __name__])

    @classmethod
    def setupClass(cls):
        cls.launch_dird_with_asset()

    @classmethod
    def teardownClass(cls):
        cls.stop_dird_with_asset()

    def lookup(self, term, profile):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}?term={term}'
        result = requests.get(url.format(profile=profile, term=term))
        return json.loads(result.text)

    def headers(self, profile):
        url = 'http://localhost:9489/0.1/directories/lookup/{profile}/headers'
        result = requests.get(url.format(profile=profile))
        return json.loads(result.text)
