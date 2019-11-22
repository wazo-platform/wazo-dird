# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from xml.dom.minidom import parseString as parse_xml
from hamcrest import assert_that, equal_to

from .helpers.base import BaseDirdIntegrationTest
from .helpers.config import new_phone_config
from .helpers.constants import VALID_TOKEN_MAIN_TENANT, VALID_UUID


class TestPhone(BaseDirdIntegrationTest):

    asset = 'phone'
    config_factory = new_phone_config

    def _get_directory_entries(self, xml_string):
        document = parse_xml(xml_string)
        results = []
        for directory_entry in document.getElementsByTagName('DirectoryEntry'):
            name = self._get_text(directory_entry.getElementsByTagName('Name')[0])
            number = self._get_text(
                directory_entry.getElementsByTagName('Telephone')[0]
            )
            results.append((name, number))
        return results

    def _get_text(self, element):
        rc = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)
