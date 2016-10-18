#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages
from setuptools.command.install_lib import install_lib as _install_lib
from distutils.command.build import build as _build


class build(_build):
    sub_commands = [('compile_catalog', None)] + _build.sub_commands


class install_lib(_install_lib):
    def run(self):
        self.run_command('compile_catalog')
        _install_lib.run(self)


class BabelWrapper(object):

    def compile_catalog(self, *args, **kwargs):
        return self.babel.compile_catalog(*args, **kwargs)

    def extract_messages(self, *args, **kwargs):
        return self.babel.extract_messages(*args, **kwargs)

    def init_catalog(self, *args, **kwargs):
        return self.babel.init_catalog(*args, **kwargs)

    def update_catalog(self, *args, **kwargs):
        return self.babel.update_catalog(*args, **kwargs)

    @property
    def babel(self):
        from babel.messages import frontend as babel
        return babel


babel_wrapper = BabelWrapper()
setup(
    name='xivo-dird',
    version='1.2',

    description='XiVO Directory Daemon',

    author='Avencall',
    author_email='dev@proformatique.com',

    url='https://github.com/xivo-pbx/xivo-dird',

    packages=find_packages(),

    include_package_data=True,
    setup_requires=['babel'],
    install_requires=['babel'],
    zip_safe=False,
    package_data={
        'xivo_dird.swagger': ['*.yml']
    },

    scripts=['bin/xivo-dird'],

    cmdclass={'build': build,
              'install_lib': install_lib,
              'compile_catalog': babel_wrapper.compile_catalog,
              'extract_messages': babel_wrapper.extract_messages,
              'init_catalog': babel_wrapper.init_catalog,
              'update_catalog': babel_wrapper.update_catalog},

    entry_points={
        'xivo_dird.services': [
            'cleanup = xivo_dird.plugins.cleanup_service:StorageCleanupServicePlugin',
            'favorites = xivo_dird.plugins.favorites_service:FavoritesServicePlugin',
            'lookup = xivo_dird.plugins.lookup:LookupServicePlugin',
            'personal = xivo_dird.plugins.personal_service:PersonalServicePlugin',
            'phonebook = xivo_dird.plugins.phonebook_service:PhonebookServicePlugin',
            'reverse = xivo_dird.plugins.reverse_service:ReverseServicePlugin',
        ],
        'xivo_dird.backends': [
            'csv = xivo_dird.plugins.csv_plugin:CSVPlugin',
            'csv_ws = xivo_dird.plugins.csv_ws:CSVWSPlugin',
            'dird_phonebook = xivo_dird.plugins.dird_phonebook:PhonebookPlugin',
            'ldap = xivo_dird.plugins.ldap_plugin:LDAPPlugin',
            'personal = xivo_dird.plugins.personal_backend:PersonalBackend',
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
            'phonebook_view = xivo_dird.plugins.phonebook_view:PhonebookViewPlugin',
        ],
    }
)
