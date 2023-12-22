# Copyright 2014-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import BaseSourcePlugin, make_result_class

DESC = (
    'It works but this wazo-dird installation is still using the default configuration'
)
SAMPLE_RESULT = {
    'id': 1,
    'firstname': 'John',
    'lastname': 'Doe',
    'number': '555',
    'description': DESC,
}


class SamplePlugin(BaseSourcePlugin):
    def load(self, args):
        self._config = args.get('config', {})
        self._name = self._config.get('name', 'sample_directory')
        self._format_columns = self._config.get(self.FORMAT_COLUMNS, {})

        backend = self._config.get('backend', '')
        SourceResult = make_result_class(
            backend, self._name, 'id', self._format_columns
        )
        self._result = SourceResult(SAMPLE_RESULT)

    def search(self, term, args=None):
        return [self._result]

    def first_match(self, term, args=None):
        return self._result

    def match_all(self, term, args=None):
        return self._result
