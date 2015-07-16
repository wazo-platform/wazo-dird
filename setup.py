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
            'privates = xivo_dird.plugins.privates_service:PrivatesServicePlugin',
        ],
        'xivo_dird.backends': [
            'broken = xivo_dird.plugins.broken_backend:BrokenPlugin',
            'csv = xivo_dird.plugins.csv_plugin:CSVPlugin',
            'csv_ws = xivo_dird.plugins.csv_ws:CSVWSPlugin',
            'ldap = xivo_dird.plugins.ldap_plugin:LDAPPlugin',
            'phonebook = xivo_dird.plugins.phonebook_plugin:PhonebookPlugin',
            'privates = xivo_dird.plugins.privates_backend:PrivatesBackend',
            'xivo = xivo_dird.plugins.xivo_user_plugin:XivoUserPlugin',
            'sample = xivo_dird.plugins.sample_backend:SamplePlugin',
        ],
        'xivo_dird.views': [
            'headers_view = xivo_dird.plugins.headers_view:HeadersViewPlugin',
            'default_json = xivo_dird.plugins.default_json_view:JsonViewPlugin',
            'privates_view = xivo_dird.plugins.privates_view:PrivatesViewPlugin',
        ],
    }
)
