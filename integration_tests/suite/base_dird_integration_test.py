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
import json
import logging

from hamcrest import assert_that
from hamcrest import equal_to

logger = logging.getLogger(__name__)

try:
    from requests.packages.urllib3 import disable_warnings
    disable_warnings()
except ImportError:
    # when disable_warnings did not exist, warnings also did not exist
    pass

ASSETS_ROOT = os.path.join(os.path.dirname(__file__), '..', 'assets')
CA_CERT = os.path.join(ASSETS_ROOT, '_common', 'ssl', 'server.crt')

VALID_TOKEN = 'valid-token'
VALID_TOKEN_1 = 'valid-token-1'
VALID_TOKEN_2 = 'valid-token-2'
VALID_TOKEN_3 = 'valid-token-3'


class BaseDirdIntegrationTest(unittest.TestCase):

    @classmethod
    def launch_dird_with_asset(cls):
        cls.container_name = cls.asset
        asset_path = os.path.join(ASSETS_ROOT, cls.asset)
        cls.cur_dir = os.getcwd()
        os.chdir(asset_path)
        cls._run_cmd('docker-compose rm --force')
        cls._run_cmd('docker-compose run --rm sync')

    @classmethod
    def dird_status(cls):
        dird_id = cls._run_cmd('docker-compose ps -q dird').strip()
        status = cls._run_cmd('docker inspect {container}'.format(container=dird_id))
        return json.loads(status)

    @classmethod
    def dird_logs(cls):
        dird_id = cls._run_cmd('docker-compose ps -q dird').strip()
        status = cls._run_cmd('docker logs {container}'.format(container=dird_id))
        return status

    @classmethod
    def stop_dird_with_asset(cls):
        cls._run_cmd('docker-compose kill')
        os.chdir(cls.cur_dir)

    @staticmethod
    def _run_cmd(cmd):
        process = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = process.communicate()
        logger.info(out)
        return out

    @classmethod
    def setUpClass(cls):
        cls.launch_dird_with_asset()

    @classmethod
    def tearDownClass(cls):
        cls.stop_dird_with_asset()

    @classmethod
    def get_lookup_result(self, term, profile, token=None):
        url = u'https://localhost:9489/0.1/directories/lookup/{profile}?term={term}'
        result = requests.get(url.format(profile=profile, term=term),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def lookup(self, term, profile, token=VALID_TOKEN):
        response = self.get_lookup_result(term, profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_headers_result(self, profile, token=None):
        url = u'https://localhost:9489/0.1/directories/lookup/{profile}/headers'
        result = requests.get(url.format(profile=profile),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def headers(self, profile):
        response = self.get_headers_result(profile, token=VALID_TOKEN)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_favorites_result(self, profile, token=None):
        url = u'https://localhost:9489/0.1/directories/favorites/{profile}'
        result = requests.get(url.format(profile=profile),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def favorites(self, profile, token=VALID_TOKEN):
        response = self.get_favorites_result(profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_favorite_result(self, directory, contact, token=None):
        url = u'https://localhost:9489/0.1/directories/favorites/{directory}/{contact}'
        result = requests.put(url.format(directory=directory, contact=contact),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def put_favorite(self, directory, contact, token=VALID_TOKEN):
        response = self.put_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_favorite_result(self, directory, contact, token=None):
        url = u'https://localhost:9489/0.1/directories/favorites/{directory}/{contact}'
        result = requests.delete(url.format(directory=directory, contact=contact),
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def delete_favorite(self, directory, contact):
        response = self.delete_favorite_result(directory, contact, token=VALID_TOKEN)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def post_personal_result(self, personal_infos, token=None):
        url = 'https://localhost:9489/0.1/personal'
        result = requests.post(url,
                               data=json.dumps(personal_infos),
                               headers={'X-Auth-Token': token,
                                        'Content-Type': 'application/json'},
                               verify=CA_CERT)
        return result

    @classmethod
    def post_personal(self, personal_infos, token=VALID_TOKEN):
        response = self.post_personal_result(personal_infos, token)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @classmethod
    def import_personal_result(self, csv, token=None, encoding='utf-8'):
        url = 'https://localhost:9489/0.1/personal/import'
        content_type = 'text/csv; charset={}'.format(encoding)
        result = requests.post(url,
                               data=csv,
                               headers={'X-Auth-Token': token,
                                        'Content-Type': content_type},
                               verify=CA_CERT)
        return result

    @classmethod
    def import_personal(self, personal_infos, token=VALID_TOKEN, encoding='utf-8'):
        response = self.import_personal_result(personal_infos, token, encoding)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @classmethod
    def list_personal_result(self, token=None):
        url = 'https://localhost:9489/0.1/personal'
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def list_personal(self, token=VALID_TOKEN):
        response = self.list_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def export_personal_result(self, token=None):
        url = 'https://localhost:9489/0.1/personal'
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT,
                              params={'format': 'text/csv'})
        return result

    @classmethod
    def export_personal(self, token=VALID_TOKEN):
        response = self.export_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_personal_result(self, personal_id, token=None):
        url = 'https://localhost:9489/0.1/personal/{contact_uuid}'
        result = requests.get(url.format(contact_uuid=personal_id),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_personal(self, personal_id, token=VALID_TOKEN):
        response = self.get_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_personal_result(self, personal_id, personal_infos, token=None):
        url = 'https://localhost:9489/0.1/personal/{contact_uuid}'
        result = requests.put(url.format(contact_uuid=personal_id),
                              data=json.dumps(personal_infos),
                              headers={'X-Auth-Token': token,
                                       'Content-Type': 'application/json'},
                              verify=CA_CERT)
        return result

    @classmethod
    def put_personal(self, personal_id, personal_infos, token=VALID_TOKEN):
        response = self.put_personal_result(personal_id, personal_infos, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def delete_personal_result(self, personal_id, token=None):
        url = 'https://localhost:9489/0.1/personal/{contact_uuid}'
        result = requests.delete(url.format(contact_uuid=personal_id),
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def delete_personal(self, personal_id, token=VALID_TOKEN):
        response = self.delete_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def purge_personal_result(self, token=None):
        url = 'https://localhost:9489/0.1/personal'
        result = requests.delete(url,
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def purge_personal(self, token=VALID_TOKEN):
        response = self.purge_personal_result(token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def get_personal_with_profile_result(self, profile, token=None):
        url = 'https://localhost:9489/0.1/directories/personal/{profile}'
        result = requests.get(url.format(profile=profile),
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_personal_with_profile(self, profile, token=VALID_TOKEN):
        response = self.get_personal_with_profile_result(profile, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_menu_cisco_result(self, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/menu/cisco'
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_menu_cisco(self, proxy=None, token=VALID_TOKEN):
        response = self.get_menu_cisco_result(proxy, token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_lookup_cisco_result(self, profile, proxy=None, term=None, token=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/cisco{query}'
        query = '?term={term}'.format(term=term) if term else ''
        result = requests.get(url.format(profile=profile,
                                         query=query),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_cisco(self, profile, proxy=None, term=None, token=VALID_TOKEN):
        response = self.get_lookup_cisco_result(profile, proxy, term, token)
        assert_that(response.status_code, equal_to(200))
        return response.text
