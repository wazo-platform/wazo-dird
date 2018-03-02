# -*- coding: utf-8 -*-
# Copyright (C) 2015 Avencall
# SPDX-License-Identifier: GPL-3.0+

from .base_dird_integration_test import BaseDirdIntegrationTest
from .base_dird_integration_test import VALID_TOKEN
from .base_dird_integration_test import VALID_UUID
from xml.dom.minidom import parseString as parse_xml

from hamcrest import assert_that
from hamcrest import equal_to


class TestPhone(BaseDirdIntegrationTest):

    asset = 'phone'

    def test_no_fallback_no_multiple_results(self):
        xml_content = self.get_lookup_cisco('test_fallback', VALID_UUID, term='Ali', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('Alice', '101')]))

    def test_fallback_no_multiple_results(self):
        xml_content = self.get_lookup_cisco('test_fallback', VALID_UUID, term='Bob', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('Bobby', '201')]))

    def test_no_fallback_multiple_results(self):
        xml_content = self.get_lookup_cisco('test_fallback', VALID_UUID, term='Char', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('Charles', '301'), ('Charles', '302')]))

    def test_no_results(self):
        xml_content = self.get_lookup_cisco('test_fallback', VALID_UUID, term='Dia', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('No entries', '')]))

    def test_fallback_multiple_results(self):
        xml_content = self.get_lookup_cisco('test_fallback', VALID_UUID, term='Eti', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('Etienne', '501'), ('Etienne', '502')]))

    def test_results_are_sorted(self):
        xml_content = self.get_lookup_cisco('test_sorted', VALID_UUID, term='A', token=VALID_TOKEN)

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('A1', '1'), ('A2', '2'), ('A3', '3')]))

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
