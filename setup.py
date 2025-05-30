#!/usr/bin/env python3
# Copyright 2016-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from setuptools import find_packages, setup

setup(
    name='wazo-dird',
    version='1.2',
    description='Wazo Directory Daemon',
    author='Wazo Authors',
    author_email='dev@wazo.community',
    url='https://wazo-platform.org',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    package_data={'wazo_dird.plugins': ['*/api.yml']},
    entry_points={
        'console_scripts': [
            'wazo-dird=wazo_dird.main:main',
            'wazo-dird-user-sync=wazo_dird.user_sync:main',
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
            'service_discovery = wazo_dird.plugins.service_discovery_service.plugin:ServiceDiscoveryServicePlugin',  # noqa
            'source = wazo_dird.plugins.source_service.plugin:SourceServicePlugin',
        ],
        'wazo_dird.backends': [
            'conference = wazo_dird.plugins.conference_backend.plugin:ConferencePlugin',
            'csv = wazo_dird.plugins.csv_backend.plugin:CSVPlugin',
            'csv_ws = wazo_dird.plugins.csv_ws_backend.plugin:CSVWSPlugin',
            'office365 = wazo_dird.plugins.office365_backend.plugin:Office365Plugin',
            'google = wazo_dird.plugins.google_backend.plugin:GooglePlugin',
            'phonebook = wazo_dird.plugins.phonebook_backend.plugin:PhonebookPlugin',
            'ldap = wazo_dird.plugins.ldap_backend.plugin:LDAPPlugin',
            'personal = wazo_dird.plugins.personal_backend.plugin:PersonalBackend',
            'wazo = wazo_dird.plugins.wazo_user_backend.plugin:WazoUserPlugin',
        ],
        'wazo_dird.views': [
            'api_view = wazo_dird.plugins.api.plugin:ApiViewPlugin',
            'backends_view = wazo_dird.plugins.backends.plugin:BackendsViewPlugin',
            'config_view = wazo_dird.plugins.config.plugin:ConfigViewPlugin',
            'conference_view = wazo_dird.plugins.conference_backend.plugin:ConferenceViewPlugin',
            'csv_backend = wazo_dird.plugins.csv_backend.plugin:CSVView',
            'csv_ws_backend = wazo_dird.plugins.csv_ws_backend.plugin:CSVWSView',
            'displays_view = wazo_dird.plugins.displays.plugin:DisplaysViewPlugin',
            'default_json = wazo_dird.plugins.default_json.plugin:JsonViewPlugin',
            'google_view = wazo_dird.plugins.google_backend.plugin:GoogleViewPlugin',
            'graphql_view = wazo_dird.plugins.graphql.plugin:GraphQLViewPlugin',
            'headers_view = wazo_dird.plugins.headers.plugin:HeadersViewPlugin',
            'ldap_backend = wazo_dird.plugins.ldap_backend.plugin:LDAPView',
            'office365_backend = wazo_dird.plugins.office365_backend.plugin:Office365View',
            'personal_view = wazo_dird.plugins.personal.plugin:PersonalViewPlugin',
            'phonebook_view = wazo_dird.plugins.phonebook.plugin:PhonebookViewPlugin',
            'phonebook_deprecated_view = wazo_dird.plugins.phonebook_deprecated.plugin:DeprecatedPhonebookViewPlugin',
            'phonebook_backend = wazo_dird.plugins.phonebook_backend.plugin:PhonebookView',
            'status_view = wazo_dird.plugins.status.plugin:StatusViewPlugin',
            'personal_backend = wazo_dird.plugins.personal_backend.plugin:PersonalView',
            'profiles_view = wazo_dird.plugins.profiles.plugin:ProfilesViewPlugin',
            'sources_view = wazo_dird.plugins.sources.plugin:SourcesViewPlugin',
            'wazo_backend = wazo_dird.plugins.wazo_user_backend.plugin:WazoUserView',
            'profile_sources_view = wazo_dird.plugins.profile_sources.plugin:SourceViewPlugin',
        ],
    },
)
