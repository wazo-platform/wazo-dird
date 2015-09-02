#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages

setup(
    name='xivo-dird',
    version='1.2',

    description='XiVO Directory Daemon',

    author='Avencall',
    author_email='dev@avencall.com',

    url='https://github.com/xivo-pbx/xivo-dird',

    packages=find_packages(),

    package_data={
        'xivo_dird.swagger': ['*.json'],
    },

    scripts=['bin/xivo-dird'],

    entry_points={
        'xivo_dird.services': [
            'favorites = xivo_dird.plugins.favorites_service:FavoritesServicePlugin',
            'lookup = xivo_dird.plugins.lookup:LookupServicePlugin',
            'personal = xivo_dird.plugins.personal_service:PersonalServicePlugin',
        ],
        'xivo_dird.backends': [
            'broken = xivo_dird.plugins.broken_backend:BrokenPlugin',
            'csv = xivo_dird.plugins.csv_plugin:CSVPlugin',
            'csv_ws = xivo_dird.plugins.csv_ws:CSVWSPlugin',
            'ldap = xivo_dird.plugins.ldap_plugin:LDAPPlugin',
            'personal = xivo_dird.plugins.personal_backend:PersonalBackend',
            'phonebook = xivo_dird.plugins.phonebook_plugin:PhonebookPlugin',
            'xivo = xivo_dird.plugins.xivo_user_plugin:XivoUserPlugin',
            'sample = xivo_dird.plugins.sample_backend:SamplePlugin',
        ],
        'xivo_dird.views': [
            'cisco_view = xivo_dird.plugins.cisco_view:CiscoViewPlugin',
            'default_json = xivo_dird.plugins.default_json_view:JsonViewPlugin',
            'headers_view = xivo_dird.plugins.headers_view:HeadersViewPlugin',
            'personal_view = xivo_dird.plugins.personal_view:PersonalViewPlugin',
        ],
    }
)
