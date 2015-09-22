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

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_TOKEN
from xml.dom.minidom import parseString as parse_xml

from hamcrest import assert_that
from hamcrest import equal_to


class TestPhone(BaseDirdIntegrationTest):

    asset = 'phone'
    profile = 'default'

    def test_no_fallback_no_multiple_results(self):
        result = self.get_lookup_cisco(term='Ali', profile=self.profile, token=VALID_TOKEN)

        results = self._get_directory_entries(result)

        assert_that(results, equal_to([('Alice', '101')]))

    def test_fallback_no_multiple_results(self):
        result = self.get_lookup_cisco(term='Bob', profile=self.profile, token=VALID_TOKEN)

        results = self._get_directory_entries(result)

        assert_that(results, equal_to([('Bobby', '201')]))

    def test_no_fallback_multiple_results(self):
        result = self.get_lookup_cisco(term='Char', profile=self.profile, token=VALID_TOKEN)

        results = self._get_directory_entries(result)

        assert_that(results, equal_to([('Charles', '301'), ('Charles', '302')]))

    def test_no_results(self):
        result = self.get_lookup_cisco(term='Dia', profile=self.profile, token=VALID_TOKEN)

        results = self._get_directory_entries(result)

        assert_that(results, equal_to([('No entries', '')]))

    def _get_directory_entries(self, xml_string):
        document = parse_xml(xml_string)
        results = []
        for directory_entry in document.getElementsByTagName('DirectoryEntry'):
            name = self._get_text(directory_entry.getElementsByTagName('Name')[0])
            number = self._get_text(directory_entry.getElementsByTagName('Telephone')[0])
            results.append((name, number))
        return results

    def _get_text(self, element):
        rc = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

