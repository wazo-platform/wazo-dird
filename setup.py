#!/usr/bin/env python3
# Copyright 2016-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

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

    @property
    def babel(self):
        from babel.messages import frontend as babel
        return babel


babel_wrapper = BabelWrapper()
setup(
    name='wazo-dird',
    version='1.2',

    description='Wazo Directory Daemon',

    author='Wazo Authors',
    author_email='dev@wazo.community',

    url='http://wazo.community',

    packages=find_packages(),

    include_package_data=True,
    setup_requires=['babel'],
    install_requires=['babel'],
    zip_safe=False,
    package_data={
        'wazo_dird.plugins.views': ['*/api.yml']
    },

    cmdclass={'build': build,
              'install_lib': install_lib,
              'compile_catalog': babel_wrapper.compile_catalog},

    entry_points={
        'console_scripts': [
            'wazo-dird=wazo_dird.main:main',
        ],
        'wazo_dird.services': [
            'cleanup = wazo_dird.plugins.cleanup_service:StorageCleanupServicePlugin',
            'config = wazo_dird.plugins.config_service:ConfigServicePlugin',
            'favorites = wazo_dird.plugins.favorites_service:FavoritesServicePlugin',
            'lookup = wazo_dird.plugins.lookup:LookupServicePlugin',
            'personal = wazo_dird.plugins.personal_service:PersonalServicePlugin',
            'phonebook = wazo_dird.plugins.phonebook_service:PhonebookServicePlugin',
            'reverse = wazo_dird.plugins.reverse_service:ReverseServicePlugin',
            'service_discovery = wazo_dird.plugins.service_discovery_service:ServiceDiscoveryServicePlugin',
        ],
        'wazo_dird.backends': [
            'csv = wazo_dird.plugins.csv_plugin:CSVPlugin',
            'csv_ws = wazo_dird.plugins.csv_ws:CSVWSPlugin',
            'dird_phonebook = wazo_dird.plugins.dird_phonebook:PhonebookPlugin',
            'ldap = wazo_dird.plugins.ldap_plugin:LDAPPlugin',
            'personal = wazo_dird.plugins.personal_backend:PersonalBackend',
            'wazo = wazo_dird.plugins.wazo_user_plugin:WazoUserPlugin',

            'sample = wazo_dird.plugins.sample_backend:SamplePlugin',
        ],
        'wazo_dird.views': [
            'api_view = wazo_dird.plugins.views.api.plugin:ApiViewPlugin',
            'backends_view = wazo_dird.plugins.views.backends.plugin:BackendsViewPlugin',
            'config_view = wazo_dird.plugins.views.config.plugin:ConfigViewPlugin',
            'default_json = wazo_dird.plugins.views.default_json.plugin:JsonViewPlugin',
            'headers_view = wazo_dird.plugins.views.headers.plugin:HeadersViewPlugin',
            'personal_view = wazo_dird.plugins.views.personal.plugin:PersonalViewPlugin',
            'phonebook_view = wazo_dird.plugins.views.phonebook.plugin:PhonebookViewPlugin',
            'aastra_view = wazo_dird.plugins.views.aastra.plugin:AastraViewPlugin',
            'cisco_view = wazo_dird.plugins.views.cisco.plugin:CiscoViewPlugin',
            'gigaset_view = wazo_dird.plugins.views.gigaset.plugin:GigasetViewPlugin',
            'htek_view = wazo_dird.plugins.views.htek.plugin:HtekViewPlugin',
            'polycom_view = wazo_dird.plugins.views.polycom.plugin:PolycomViewPlugin',
            'snom_view = wazo_dird.plugins.views.snom.plugin:SnomViewPlugin',
            'thomson_view = wazo_dird.plugins.views.thomson.plugin:ThomsonViewPlugin',
            'yealink_view = wazo_dird.plugins.views.yealink.plugin:YealinkViewPlugin',
        ],
    }
)
