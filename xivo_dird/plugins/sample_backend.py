# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

from xivo_dird import BaseSourcePlugin
from xivo_dird import make_result_class


class SamplePlugin(BaseSourcePlugin):

    _sample_result = {
        'id': 1,
        'firstname': 'John',
        'lastname': 'Doe',
        'description': 'It works but this xivo-dird installation is still using the default configuration',
    }

    def load(self, args):
        self._config = args.get('config', {})
        self._name = self._config.get('name', 'sample_directory')
        self._source_to_display = self._config.get(self.SOURCE_TO_DISPLAY, {})
        SourceResult = make_result_class(self._name, 'id', self._source_to_display)
        self._result = SourceResult(self._sample_result)

    def search(self, term, profile=None, args=None):
        return [self._result]
