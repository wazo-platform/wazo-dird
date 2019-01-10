# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import os
import json
import logging
from contextlib import contextmanager

import requests
from hamcrest import (
    assert_that,
    equal_to,
)
from stevedore import DriverManager

from xivo import url_helpers
from xivo_test_helpers import until
from xivo_test_helpers.asset_launching_test_case import AssetLaunchingTestCase
from xivo_test_helpers.db import DBUserClient

logger = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

ASSET_ROOT = os.path.join(os.path.dirname(__file__), '..', 'assets')
CA_CERT = os.path.join(ASSET_ROOT, 'ssl', 'dird', 'server.crt')
DB_URI = os.getenv('DB_URI', 'postgresql://asterisk:proformatique@localhost:{port}/asterisk')

VALID_UUID = 'uuid'
VALID_UUID_1 = 'uuid-1'

VALID_TOKEN = 'valid-token'
VALID_TOKEN_1 = 'valid-token-1'
VALID_TOKEN_2 = 'valid-token-2'
VALID_TOKEN_NO_ACL = 'valid-token-no-acl'


def absolute_file_name(asset_name, path):
    dirname, basename = os.path.split(path)
    real_basename = 'asset.{}.{}'.format(asset_name, basename)
    return os.path.join(ASSET_ROOT, dirname, real_basename)


class BackendWrapper:

    def __init__(self, backend, config):
        manager = DriverManager(namespace='wazo_dird.backends',
                                name=backend,
                                invoke_on_load=True)
        self._source = manager.driver
        self._source.load(config)

    def unload(self):
        self._source.unload()

    def search(self, term):
        return [r.fields for r in self.search_raw(term)]

    def search_raw(self, term):
        return self._source.search(term)

    def first(self, term):
        return self._source.first_match(term).fields

    def list(self, source_ids):
        results = self._source.list(source_ids)
        return [r.fields for r in results]


class BaseDirdIntegrationTest(AssetLaunchingTestCase):

    assets_root = ASSET_ROOT
    service = 'dird'

    @classmethod
    def url(cls, *parts):
        port = cls.service_port(9489, 'dird')
        base = 'https://localhost:{port}/0.1/'.format(port=port)
        return url_helpers.base_join(base, *parts)

    @classmethod
    def get_config(cls, token):
        url = cls.url('config')
        return requests.get(url, headers={'X-Auth-Token': token}, verify=CA_CERT).json()

    @classmethod
    def get_lookup_result(cls, term, profile, token=None):
        params = {'term': term}
        url = cls.url('directories', 'lookup', profile)
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def lookup(cls, term, profile, token=VALID_TOKEN):
        response = cls.get_lookup_result(term, profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_headers_result(cls, profile, token=None):
        url = cls.url('directories', 'lookup', profile, 'headers')
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def headers(cls, profile):
        response = cls.get_headers_result(profile, token=VALID_TOKEN)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_reverse_result(cls, exten, profile, xivo_user_uuid, token=None):
        params = {'exten': exten}
        url = cls.url('directories', 'reverse', profile, xivo_user_uuid)
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def reverse(cls, exten, profile, xivo_user_uuid, token=VALID_TOKEN):
        response = cls.get_reverse_result(exten, profile, xivo_user_uuid, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_favorites_result(cls, profile, token=None):
        url = cls.url('directories', 'favorites', profile)
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def favorites(cls, profile, token=VALID_TOKEN):
        response = cls.get_favorites_result(profile, token=token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def put_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        result = requests.put(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def put_favorite(cls, directory, contact, token=VALID_TOKEN):
        response = cls.put_favorite_result(directory, contact, token=token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_favorite_result(cls, directory, contact, token=None):
        url = cls.url('directories', 'favorites', directory, contact)
        result = requests.delete(url,
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def delete_favorite(cls, directory, contact):
        response = cls.delete_favorite_result(directory, contact, token=VALID_TOKEN)
        assert_that(response.status_code, equal_to(204))

    @contextmanager
    def favorite(self, source, source_entry_id, token=VALID_TOKEN):
        self.put_favorite(source, source_entry_id, token)
        try:
            yield
        finally:
            self.delete_favorite_result(source, source_entry_id, token)

    @classmethod
    def post_phonebook(cls, tenant, phonebook_body, token=VALID_TOKEN):
        return requests.post(
            cls.url('tenants', tenant, 'phonebooks'),
            data=json.dumps(phonebook_body),
            headers={'X-Auth-Token': token, 'Content-Type': 'application/json'},
            verify=CA_CERT,
        )

    @classmethod
    def put_phonebook(cls, tenant, phonebook_id, phonebook_body, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        response = requests.put(url,
                                data=json.dumps(phonebook_body),
                                headers={'X-Auth-Token': token,
                                         'Content-Type': 'application/json'},
                                verify=CA_CERT)
        return response.json()

    @classmethod
    def post_phonebook_contact(cls, tenant, phonebook_id, contact_body, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        response = requests.post(url,
                                 data=json.dumps(contact_body),
                                 headers={'X-Auth-Token': token,
                                          'Content-Type': 'application/json'},
                                 verify=CA_CERT)
        return response.json()

    @classmethod
    def put_phonebook_contact(cls, tenant, phonebook_id, contact_uuid, contact_body, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid)
        response = requests.put(url,
                                data=json.dumps(contact_body),
                                headers={'X-Auth-Token': token,
                                         'Content-Type': 'application/json'},
                                verify=CA_CERT)
        return response.json()

    @classmethod
    def post_personal_result(cls, personal_infos, token=None):
        url = cls.url('personal')
        result = requests.post(url,
                               data=json.dumps(personal_infos),
                               headers={'X-Auth-Token': token,
                                        'Content-Type': 'application/json'},
                               verify=CA_CERT)
        return result

    @classmethod
    def post_personal(cls, personal_infos, token=VALID_TOKEN):
        response = cls.post_personal_result(personal_infos, token)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @contextmanager
    def personal(self, personal_infos, token=VALID_TOKEN):
        response = self.post_personal(personal_infos, token)
        try:
            yield response
        finally:
            self.delete_personal_result(response['id'], token)

    @classmethod
    def import_personal_result(cls, csv, token=None, encoding='utf-8'):
        url = cls.url('personal', 'import')
        content_type = 'text/csv; charset={}'.format(encoding)
        result = requests.post(url,
                               data=csv,
                               headers={'X-Auth-Token': token,
                                        'Content-Type': content_type},
                               verify=CA_CERT)
        return result

    @classmethod
    def import_personal(cls, personal_infos, token=VALID_TOKEN, encoding='utf-8'):
        response = cls.import_personal_result(personal_infos, token, encoding)
        assert_that(response.status_code, equal_to(201))
        return response.json()

    @classmethod
    def list_personal_result(cls, token=None):
        url = cls.url('personal')
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def list_personal(cls, token=VALID_TOKEN):
        response = cls.list_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def list_phonebooks(cls, tenant, token=None):
        token = token or VALID_TOKEN
        url = cls.url('tenants', tenant, 'phonebooks')
        response = requests.get(url, headers={'X-Auth-Token': token}, verify=CA_CERT)
        return response.json()['items']

    @classmethod
    def export_personal_result(cls, token=None):
        url = cls.url('personal')
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT,
                              params={'format': 'text/csv'})
        return result

    @classmethod
    def export_personal(cls, token=VALID_TOKEN):
        response = cls.export_personal_result(token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_personal(cls, personal_id, token=VALID_TOKEN):
        response = cls.get_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_phonebook(cls, tenant, phonebook_id, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        response = requests.get(url,
                                headers={'X-Auth-Token': token},
                                verify=CA_CERT)
        return response.json()

    @classmethod
    def get_phonebook_contact(cls, tenant, phonebook_id, contact_uuid, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts', contact_uuid)
        response = requests.get(url,
                                headers={'X-Auth-Token': token},
                                verify=CA_CERT)
        return response.json()

    @classmethod
    def list_phonebook_contacts(cls, tenant, phonebook_id, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id, 'contacts')
        response = requests.get(url,
                                headers={'X-Auth-Token': token},
                                verify=CA_CERT)
        return response.json()['items']

    @classmethod
    def put_personal_result(cls, personal_id, personal_infos, token=None):
        url = cls.url('personal', personal_id)
        result = requests.put(url,
                              data=json.dumps(personal_infos),
                              headers={'X-Auth-Token': token,
                                       'Content-Type': 'application/json'},
                              verify=CA_CERT)
        return result

    @classmethod
    def put_personal(cls, personal_id, personal_infos, token=VALID_TOKEN):
        response = cls.put_personal_result(personal_id, personal_infos, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def delete_personal_result(cls, personal_id, token=None):
        url = cls.url('personal', personal_id)
        result = requests.delete(url,
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def delete_personal(cls, personal_id, token=VALID_TOKEN):
        response = cls.delete_personal_result(personal_id, token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def delete_phonebook(cls, tenant, phonebook_id, token=VALID_TOKEN):
        url = cls.url('tenants', tenant, 'phonebooks', phonebook_id)
        requests.delete(url,
                        headers={'X-Auth-Token': token},
                        verify=CA_CERT)

    @classmethod
    def purge_personal_result(cls, token=None):
        url = cls.url('personal')
        result = requests.delete(url,
                                 headers={'X-Auth-Token': token},
                                 verify=CA_CERT)
        return result

    @classmethod
    def purge_personal(cls, token=VALID_TOKEN):
        response = cls.purge_personal_result(token)
        assert_that(response.status_code, equal_to(204))

    @classmethod
    def get_personal_with_profile_result(cls, profile, token=None):
        url = cls.url('directories', 'personal', profile)
        result = requests.get(url,
                              headers={'X-Auth-Token': token},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_personal_with_profile(cls, profile, token=VALID_TOKEN):
        response = cls.get_personal_with_profile_result(profile, token)
        assert_that(response.status_code, equal_to(200))
        return response.json()

    @classmethod
    def get_menu_cisco_result(cls, profile, xivo_user_uuid, proxy=None, token=None):
        url = cls.url('directories', 'menu', profile, xivo_user_uuid, 'cisco')
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_menu_cisco(cls, profile, xivo_user_uuid, proxy=None, token=VALID_TOKEN):
        response = cls.get_menu_cisco_result(profile, xivo_user_uuid, proxy, token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_input_cisco_result(cls, profile, xivo_user_uuid, proxy=None, token=None):
        url = cls.url('directories', 'input', profile, xivo_user_uuid, 'cisco')
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_cisco(cls, profile, xivo_user_uuid, proxy=None, token=VALID_TOKEN):
        response = cls.get_input_cisco_result(profile, xivo_user_uuid, proxy, token)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_lookup_cisco_result(cls, profile, xivo_user_uuid,
                                proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'cisco')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_cisco(cls, profile, xivo_user_uuid, term, proxy=None, token=VALID_TOKEN, limit=None, offset=None):
        response = cls.get_lookup_cisco_result(profile, xivo_user_uuid, proxy, term, token, limit, offset)
        assert_that(response.status_code, equal_to(200))
        return response.text

    @classmethod
    def get_input_aastra_result(cls, profile, xivo_user_uuid, proxy=None, token=None):
        url = cls.url('directories', 'input', profile, xivo_user_uuid, 'aastra')
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_aastra_result(cls, profile, xivo_user_uuid,
                                 proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'aastra')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_polycom_result(cls, profile, xivo_user_uuid, proxy=None, token=None):
        url = cls.url('directories', 'input', profile, xivo_user_uuid, 'polycom')
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_polycom_result(cls, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'polycom')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_input_snom_result(cls, profile, xivo_user_uuid, proxy=None, token=None):
        url = cls.url('directories', 'input', profile, xivo_user_uuid, 'snom')
        result = requests.get(url,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_snom_result(cls, profile, xivo_user_uuid,
                               proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'snom')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_thomson_result(cls, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'thomson')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_yealink_result(cls, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'yealink')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_gigaset_result(cls, profile, xivo_user_uuid,
                                  proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'gigaset')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def get_lookup_htek_result(cls, profile, xivo_user_uuid,
                               proxy=None, term=None, token=None, limit=None, offset=None):
        url = cls.url('directories', 'lookup', profile, xivo_user_uuid, 'htek')
        params = {'term': term, 'limit': limit, 'offset': offset}
        result = requests.get(url,
                              params=params,
                              headers={'X-Auth-Token': token,
                                       'Proxy-URL': proxy},
                              verify=CA_CERT)
        return result

    @classmethod
    def new_db_client(cls):
        db_uri = DB_URI.format(port=cls.service_port(5432, 'db'))
        return DBUserClient(db_uri)

    @classmethod
    def restart_postgres(cls):
        cls.restart_service('db', signal='SIGINT')  # fast shutdown
        database = cls.new_db_client()
        until.true(database.is_up, timeout=5, message='Postgres did not come back up')
