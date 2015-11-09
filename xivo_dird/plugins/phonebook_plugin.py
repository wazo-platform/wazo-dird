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

import logging
import re
import requests

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class

logger = logging.getLogger(__name__)


class PhonebookPlugin(BaseSourcePlugin):

    def __init__(self, *args, **kwargs):
        super(PhonebookPlugin, self).__init__(*args, **kwargs)
        self.pbook_factory = _PhonebookFactory()

    def load(self, args):
        pbook_config = self.pbook_factory.new_phonebook_config(args['config'])
        self._pbook_client = self.pbook_factory.new_phonebook_client(pbook_config)
        self._pbook_result_converter = self.pbook_factory.new_phonebook_result_converter(pbook_config)

    def search(self, term, args=None):
        term = term.encode('UTF-8')

        return self._pbook_result_converter.convert_all(self._pbook_client.search(term))

    def first_match(self, term, args=None):
        term = term.encode('utf-8')
        result = self._pbook_client.first_match(term)

        if result is not None:
            return self._pbook_result_converter.convert(result)
        return result


class _PhonebookFactory(object):

    def new_phonebook_config(self, config):
        return _PhonebookConfig(config)

    def new_phonebook_client(self, pbook_config):
        return _PhonebookClient(pbook_config)

    def new_phonebook_result_converter(self, pbook_config):
        return _PhonebookResultConverter(pbook_config)


class _PhonebookConfig(object):

    DEFAULT_PHONEBOOK_URL = 'http://localhost/service/ipbx/json.php/private/pbx_services/phonebook'
    DEFAULT_PHONEBOOK_TIMEOUT = 1.0

    def __init__(self, config):
        self._config = config

    def name(self):
        return self._config['name']

    def format_columns(self):
        return self._config[BaseSourcePlugin.FORMAT_COLUMNS]

    def first_matched_columns(self):
        return self._config[BaseSourcePlugin.FIRST_MATCHED_COLUMNS]

    def looked_up_keys(self):
        results = set()

        for format_string in self.format_columns().itervalues():
            for key in re.findall(r'{([\w.]+)}', format_string):
                results.add(key)

        return list(results)

    def phonebook_url(self):
        return self._config.get('phonebook_url', self.DEFAULT_PHONEBOOK_URL)

    def phonebook_username(self):
        return self._config.get('phonebook_username')

    def phonebook_password(self):
        return self._config.get('phonebook_password')

    def phonebook_timeout(self):
        return self._config.get('phonebook_timeout', self.DEFAULT_PHONEBOOK_TIMEOUT)


class _PhonebookClient(object):

    def __init__(self, pbook_config):
        self._name = pbook_config.name()
        self._url = pbook_config.phonebook_url()
        self._timeout = pbook_config.phonebook_timeout()
        self._auth = self._new_auth(pbook_config)
        self._first_matched_fetchers = [_Fetcher(key, pbook_config.name())
                                        for key in pbook_config.first_matched_columns()]

    def _new_auth(self, pbook_config):
        username = pbook_config.phonebook_username()
        password = pbook_config.phonebook_password()
        if username and password:
            return requests.auth.HTTPBasicAuth(username, password)
        return None

    def first_match(self, term):
        results = self.search(term)

        for result in results:
            for fetcher in self._first_matched_fetchers:
                if fetcher(result) == term:
                    return result
        return None

    def search(self, term):
        contacts = []
        params = {'act': 'search', 'search': term}
        try:
            r = requests.get(self._url, params=params, auth=self._auth, timeout=self._timeout, verify=False)
        except requests.exceptions.Timeout:
            logger.warning('Phonebook "%s": request error: timed out', self._name)
        except Exception as e:
            logger.error('Phonebook "%s": request error: %r', self._name, e)
        else:
            if r.status_code == 200:
                contacts = r.json()
            elif r.status_code != 204:
                logger.warning('Phonebook "%s": unexpected HTTP status code %s', self._name, r.status_code)

        return contacts


class _PhonebookResultConverter(object):

    def __init__(self, pbook_config):
        self._format_columns = pbook_config.format_columns()
        self._SourceResult = make_result_class(pbook_config.name())
        self._fetchers = [_Fetcher(key, pbook_config.name()) for key in pbook_config.looked_up_keys()]

    def convert(self, raw_result):
        mapping = dict((fetcher._key, fetcher(raw_result)) for fetcher in self._fetchers)
        fields = dict((column, self._format_value(format_string, mapping))
                      for column, format_string in self._format_columns.iteritems())
        return self._SourceResult(fields)

    def convert_all(self, raw_results):
        return [self.convert(raw_result) for raw_result in raw_results]

    def _format_value(self, format_string, mapping):
        valid_format_string = unicode(format_string.replace('.', '/'))
        return valid_format_string.format(**mapping).strip() or None


class _Fetcher(object):

    _IGNORED_MISSING_KEYS = ['phonebooknumber/home/number',
                             'phonebooknumber/mobile/number',
                             'phonebooknumber/office/number',
                             'phonebooknumber/other/number']

    def __init__(self, key, name):
        self._key = key.replace('.', '/')
        self._name = name
        self._keys = key.split('.')

    def __call__(self, raw_result):
        v = raw_result
        try:
            for k in self._keys:
                v = v[k]
        except KeyError:
            if self._key not in self._IGNORED_MISSING_KEYS:
                logger.warning('Phonebook "%s": could not map %r: no such key', self._name, self._key)
            return ''
        except TypeError as e:
            if v is not False:
                logger.warning('Phonebook "%s": could not map %r: type error: %s', self._name, self._key, e)
            return ''
        return v
