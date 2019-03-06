# Copyright 2014-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseSourcePlugin
from wazo_dird import make_result_class


class SamplePlugin(BaseSourcePlugin):

    _sample_result = {
        'id': 1,
        'firstname': 'John',
        'lastname': 'Doe',
        'number': '555',
        'description': 'It works but this wazo-dird installation is still using the default configuration',
    }

    def load(self, args):
        self._config = args.get('config', {})
        self._name = self._config.get('name', 'sample_directory')
        self._format_columns = self._config.get(self.FORMAT_COLUMNS, {})
        SourceResult = make_result_class(self._name, 'id', self._format_columns)
        self._result = SourceResult(self._sample_result)

    def search(self, term, args=None):
        return [self._result]

    def first_match(self, term, args=None):
        return self._result
