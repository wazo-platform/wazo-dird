# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

from xml.dom.minidom import parseString as parse_xml
from hamcrest import (
    assert_that,
    equal_to,
)

from .base_dird_integration_test import (
    BaseDirdIntegrationTest,
    VALID_TOKEN_MAIN_TENANT,
    VALID_UUID,
)


class TestPhone(BaseDirdIntegrationTest):

    asset = 'phone'
    displays = [
        {
            'name': 'default',
            'columns': [
                {
                    'field': 'phone',
                    'type': 'number',
                    'number_display': '{display_name}',
                },
            ],
        },
        {
            'name': 'test_fallback',
            'columns': [
                {
                    'field': 'phone',
                    'type': 'number',
                    'number_display': '{display_name}',
                },
                {
                    'field': 'phone1',
                    'type': 'number',
                    'number_display': '{display_name1}',
                },
            ],
        },
    ]
    sources = [
        {
            'backend': 'csv',
            'name': 'test_sorted',
            'file': '/tmp/data/test_sorted.csv',
            'searched_columns': ['fn'],
            'format_columns': {
                'display_name': "{fn}",
                'phone': "{num}",
            },
        },
        {
            'backend': 'csv',
            'name': 'test_fallback',
            'file': '/tmp/data/test_fallback.csv',
            'searched_columns': ['fn', 'fn1'],
            'format_columns': {
                'display_name': "{fn}",
                'display_name1': "{fn1}",
                'phone': "{num}",
                'phone1': "{num1}",
            },
        }
    ]
    profiles = [
        {
            'name': 'test_fallback',
            'display': 'test_fallback',
            'services': {'lookup': {'sources': ['test_fallback']}},
        },
        {
            'name': 'test_sorted',
            'display': 'default',
            'services': {'lookup': {'sources': ['test_sorted']}},
        },
    ]

    def test_no_fallback_no_multiple_results(self):
        xml_content = self.get_lookup_cisco(
            'test_fallback', VALID_UUID, term='Ali', token=VALID_TOKEN_MAIN_TENANT,
        )

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('Alice', '101')]))

    def test_no_results(self):
        xml_content = self.get_lookup_cisco(
            'test_fallback', VALID_UUID, term='Dia', token=VALID_TOKEN_MAIN_TENANT,
        )

        results = self._get_directory_entries(xml_content)

        assert_that(results, equal_to([('No entries', '')]))

    def test_results_are_sorted(self):
        xml_content = self.get_lookup_cisco(
            'test_sorted', VALID_UUID, term='A', token=VALID_TOKEN_MAIN_TENANT,
        )

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
