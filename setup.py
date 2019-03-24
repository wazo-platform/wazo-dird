#!/usr/bin/env python3
# Copyright 2016-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

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
        'wazo_dird.plugins': ['*/api.yml']
    },

    cmdclass={'build': build,
              'install_lib': install_lib,
              'compile_catalog': babel_wrapper.compile_catalog},

    entry_points={
        'console_scripts': [
            'wazo-dird=wazo_dird.main:main',
        ],
        'wazo_dird.services': [
            'cleanup = wazo_dird.plugins.cleanup_service.plugin:StorageCleanupServicePlugin',
            'config = wazo_dird.plugins.config_service.plugin:ConfigServicePlugin',
            'display = wazo_dird.plugins.display_service.plugin:DisplayServicePlugin',
            'favorites = wazo_dird.plugins.favorites_service.plugin:FavoritesServicePlugin',
            'lookup = wazo_dird.plugins.lookup_service.plugin:LookupServicePlugin',
            'personal = wazo_dird.plugins.personal_service.plugin:PersonalServicePlugin',
            'phonebook = wazo_dird.plugins.phonebook_service.plugin:PhonebookServicePlugin',
            'profile = wazo_dird.plugins.profile_service.plugin:ProfileServicePlugin',
            'reverse = wazo_dird.plugins.reverse_service.plugin:ReverseServicePlugin',
            'service_discovery = wazo_dird.plugins.service_discovery_service.plugin:ServiceDiscoveryServicePlugin',
            'source = wazo_dird.plugins.source_service.plugin:SourceServicePlugin',
        ],
        'wazo_dird.backends': [
            'csv = wazo_dird.plugins.csv_backend.plugin:CSVPlugin',
            'csv_ws = wazo_dird.plugins.csv_ws_backend.plugin:CSVWSPlugin',
            'phonebook = wazo_dird.plugins.phonebook_backend.plugin:PhonebookPlugin',
            'ldap = wazo_dird.plugins.ldap_backend.plugin:LDAPPlugin',
            'personal = wazo_dird.plugins.personal_backend.plugin:PersonalBackend',
            'wazo = wazo_dird.plugins.wazo_user_backend.plugin:WazoUserPlugin',
        ],
        'wazo_dird.views': [
            'api_view = wazo_dird.plugins.api.plugin:ApiViewPlugin',
            'backends_view = wazo_dird.plugins.backends.plugin:BackendsViewPlugin',
            'config_view = wazo_dird.plugins.config.plugin:ConfigViewPlugin',
            'csv_backend = wazo_dird.plugins.csv_backend.plugin:CSVView',
            'csv_ws_backend = wazo_dird.plugins.csv_ws_backend.plugin:CSVWSView',
            'displays_view = wazo_dird.plugins.displays.plugin:DisplaysViewPlugin',
            'default_json = wazo_dird.plugins.default_json.plugin:JsonViewPlugin',
            'headers_view = wazo_dird.plugins.headers.plugin:HeadersViewPlugin',
            'ldap_backend = wazo_dird.plugins.ldap_backend.plugin:LDAPView',
            'personal_view = wazo_dird.plugins.personal.plugin:PersonalViewPlugin',
            'phonebook_view = wazo_dird.plugins.phonebook.plugin:PhonebookViewPlugin',
            'phonebook_backend = wazo_dird.plugins.phonebook_backend.plugin:PhonebookView',
            'tenant_migration = wazo_dird.plugins.phonebook_tenant_modifier.plugin:PhonebookTenantMoverPlugin',
            'aastra_view = wazo_dird.plugins.aastra.plugin:AastraViewPlugin',
            'cisco_view = wazo_dird.plugins.cisco.plugin:CiscoViewPlugin',
            'gigaset_view = wazo_dird.plugins.gigaset.plugin:GigasetViewPlugin',
            'htek_view = wazo_dird.plugins.htek.plugin:HtekViewPlugin',
            'personal_backend = wazo_dird.plugins.personal_backend.plugin:PersonalView',
            'polycom_view = wazo_dird.plugins.polycom.plugin:PolycomViewPlugin',
            'profiles_view = wazo_dird.plugins.profiles.plugin:ProfilesViewPlugin',
            'snom_view = wazo_dird.plugins.snom.plugin:SnomViewPlugin',
            'thomson_view = wazo_dird.plugins.thomson.plugin:ThomsonViewPlugin',
            'yealink_view = wazo_dird.plugins.yealink.plugin:YealinkViewPlugin',
            'wazo_backend = wazo_dird.plugins.wazo_user_backend.plugin:WazoUserView',
        ],
    }
)
