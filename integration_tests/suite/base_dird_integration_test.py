# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
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

import requests
import os
import json
import logging

from hamcrest import assert_that
from hamcrest import equal_to
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

ASSET_ROOT = os.path.join(os.path.dirname(__file__), '..', 'assets')
CA_CERT = os.path.join(ASSET_ROOT, '_common', 'ssl', 'server.crt')

VALID_UUID = 'uuid'
VALID_UUID_1 = 'uuid-1'

VALID_TOKEN = 'valid-token'
VALID_TOKEN_1 = 'valid-token-1'
VALID_TOKEN_2 = 'valid-token-2'
VALID_TOKEN_NO_ACL = 'valid-token-no-acl'


class BaseDirdIntegrationTest(AssetLaunchingTestCase):

    assets_root = ASSET_ROOT
    service = 'dird'

    @classmethod
    def get_lookup_result(self, term, profile, token=None):
        params = {'term': term}
        url = u'https://localhost:9489/0.1/directories/lookup/{profile}'
        result = requests.get(url.format(profile=profile),
                              params=params,
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
    def get_reverse_result(self, exten, profile, xivo_user_uuid, token=None):
        params = {'exten': exten}
        url = u'https://localhost:9489/0.1/directories/reverse/{profile}/{xivo_user_uuid}'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def reverse(self, exten, profile, xivo_user_uuid, token=VALID_TOKEN):
        response = self.get_reverse_result(exten, profile, xivo_user_uuid, token=token)
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
    def get_menu_cisco_result(self, profile, xivo_user_uuid, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/menu/{profile}/{xivo_user_uuid}/cisco'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_menu_cisco(self, profile, xivo_user_uuid, proxy=None, token=VALID_TOKEN):
        response = self.get_menu_cisco_result(profile, xivo_user_uuid, proxy, token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_input_cisco_result(self, profile, xivo_user_uuid, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/input/{profile}/{xivo_user_uuid}/cisco'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_cisco(self, profile, xivo_user_uuid, proxy=None, token=VALID_TOKEN):
        response = self.get_input_cisco_result(profile, xivo_user_uuid, proxy, token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_lookup_cisco_result(self, profile, xivo_user_uuid,
                                proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/cisco'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_cisco(self, profile, xivo_user_uuid, term, proxy=None, token=VALID_TOKEN, limit=None, offset=None):
        response = self.get_lookup_cisco_result(profile, xivo_user_uuid, proxy, term, token, limit, offset)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_input_aastra_result(self, profile, xivo_user_uuid, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/input/{profile}/{xivo_user_uuid}/aastra'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_aastra_result(self, profile, xivo_user_uuid,
                                 proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/aastra'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_polycom_result(self, profile, xivo_user_uuid, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/input/{profile}/{xivo_user_uuid}/polycom'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_polycom_result(self, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/polycom'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_snom_result(self, profile, xivo_user_uuid, proxy=None, token=None):
        url = 'https://localhost:9489/0.1/directories/input/{profile}/{xivo_user_uuid}/snom'
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_snom_result(self, profile, xivo_user_uuid,
                               proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/snom'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_thomson_result(self, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/thomson'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_yealink_result(self, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = 'https://localhost:9489/0.1/directories/lookup/{profile}/{xivo_user_uuid}/yealink'
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url.format(profile=profile, xivo_user_uuid=xivo_user_uuid),
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result
