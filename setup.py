#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages
from setuptools.command.install_lib import install_lib as _install_lib
from distutils.command.build import build as _build
from babel.messages import frontend as babel


class build(_build):
    sub_commands = [('compile_catalog', None)] + _build.sub_commands


class install_lib(_install_lib):
    def run(self):
        self.run_command('compile_catalog')
        _install_lib.run(self)


setup(
    name='xivo-dird',
    version='1.2',

    description='XiVO Directory Daemon',

    author='Avencall',
    author_email='dev@avencall.com',

    url='https://github.com/xivo-pbx/xivo-dird',

    packages=find_packages(),

    include_package_data=True,
    zip_safe=False,
    package_data={
        'xivo_dird.swagger': ['*.json']
    },

    scripts=['bin/xivo-dird'],

    cmdclass={'build': build, 'install_lib': install_lib,
              'compile_catalog': babel.compile_catalog,
              'extract_messages': babel.extract_messages,
              'init_catalog': babel.init_catalog,
              'update_catalog': babel.update_catalog},

    entry_points={
        'xivo_dird.services': [
            'favorites = xivo_dird.plugins.favorites_service:FavoritesServicePlugin',
            'lookup = xivo_dird.plugins.lookup:LookupServicePlugin',
            'personal = xivo_dird.plugins.personal_service:PersonalServicePlugin',
        ],
        'xivo_dird.backends': [
            'csv = xivo_dird.plugins.csv_plugin:CSVPlugin',
            'csv_ws = xivo_dird.plugins.csv_ws:CSVWSPlugin',
            'ldap = xivo_dird.plugins.ldap_plugin:LDAPPlugin',
            'personal = xivo_dird.plugins.personal_backend:PersonalBackend',
            'phonebook = xivo_dird.plugins.phonebook_plugin:PhonebookPlugin',
            'xivo = xivo_dird.plugins.xivo_user_plugin:XivoUserPlugin',
            'sample = xivo_dird.plugins.sample_backend:SamplePlugin',
        ],
        'xivo_dird.views': [
            'aastra_view = xivo_dird.plugins.aastra_view:AastraViewPlugin',
            'cisco_view = xivo_dird.plugins.cisco_view:CiscoViewPlugin',
            'polycom_view = xivo_dird.plugins.polycom_view:PolycomViewPlugin',
            'snom_view = xivo_dird.plugins.snom_view:SnomViewPlugin',
            'thomson_view = xivo_dird.plugins.thomson_view:ThomsonViewPlugin',
            'yealink_view = xivo_dird.plugins.yealink_view:YealinkViewPlugin',
            'default_json = xivo_dird.plugins.default_json_view:JsonViewPlugin',
            'headers_view = xivo_dird.plugins.headers_view:HeadersViewPlugin',
            'personal_view = xivo_dird.plugins.personal_view:PersonalViewPlugin',
        ],
    }
)
