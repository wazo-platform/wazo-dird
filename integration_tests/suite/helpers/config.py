# Copyright 2019-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import string

from wazo_dird import database

from .constants import MAIN_TENANT, SUB_TENANT, TENANT_UUID_2


def _random_string(n):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(n))


DEFAULT_DISPLAY = {
    'tenant_uuid': MAIN_TENANT,
    'name': 'default_display',
    'columns': [
        {'title': 'Firstname', 'field': 'firstname'},
        {'title': 'Lastname', 'field': 'lastname'},
        {'title': 'Number', 'field': 'number'},
    ],
}


class Config:
    def __init__(self, Session):
        self.display_crud = database.DisplayCRUD(Session)
        self.profile_crud = database.ProfileCRUD(Session)
        self.source_crud = database.SourceCRUD(Session)

        self.profiles = []
        self.displays = []
        self.sources = []

        self.created_profiles = {}
        self.created_displays = {}
        self.created_sources = {}

    def setup(self):
        self._create_displays()
        self._create_sources()
        self._create_profiles()

    def tear_down(self):
        self._remove_profiles()
        self._remove_sources()
        self._remove_displays()

    def with_profile(self, **profile_args):
        profile_args.setdefault('name', _random_string(10))
        profile_args.setdefault('tenant_uuid', MAIN_TENANT)
        profile_args.setdefault('services', {})
        profile_args.setdefault('display', None)

        self.profiles.append(profile_args)

    def with_display(self, **display_args):
        display_args.setdefault('name', _random_string(16))
        display_args.setdefault('tenant_uuid', MAIN_TENANT)
        display_args.setdefault('columns', [])

        self.displays.append(display_args)

    def with_source(self, **source_args):
        source_args.setdefault('tenant_uuid', MAIN_TENANT)
        source_args.setdefault('searched_columns', [])
        source_args.setdefault('first_matched_columns', [])
        source_args.setdefault('format_columns', {})

        self.sources.append(source_args)

    def _create_displays(self):
        for display in self.displays:
            new_display = self.display_crud.create(**display)
            self.created_displays[new_display['name']] = new_display

    def _create_profiles(self):
        for profile in self.profiles:
            body = dict(profile)
            body['display'] = self.created_displays[profile['display']]
            for service_config in body['services'].values():
                sources = []
                for source_name in service_config['sources']:
                    sources.append(self.created_sources[source_name])
                service_config['sources'] = sources

            new_profile = self.profile_crud.create(body)
            self.created_profiles[new_profile['name']] = new_profile

    def _create_sources(self):
        for source in self.sources:
            body = dict(source)
            backend = body.pop('backend')
            new_source = self.source_crud.create(backend, body)
            self.created_sources[new_source['name']] = new_source

    def _remove_displays(self):
        for display in self.created_displays.values():
            visible_tenants = [display['tenant_uuid']]
            try:
                self.display_crud.delete(visible_tenants, display['uuid'])
            except Exception:
                continue

    def _remove_profiles(self):
        for profile in self.created_profiles.values():
            visible_tenants = [profile['tenant_uuid']]
            self.profile_crud.delete(visible_tenants, profile['uuid'])

    def _remove_sources(self):
        for source in self.created_sources.values():
            visible_tenants = [source['tenant_uuid']]
            backend = source['backend']
            self.source_crud.delete(backend, source['uuid'], visible_tenants)


def new_auth_only_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_profile(name='default', display='default_display')
    return config


def new_conference_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'default': '', 'field': 'exten'},
            {'title': 'Mobile', 'default': '', 'field': 'mobile_phone_number'},
        ],
    )
    config.with_source(
        backend='conference',
        name='confs',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['name'],
    )
    config.with_source(
        tenant_uuid=SUB_TENANT,
        backend='conference',
        name='confs_sub',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['name'],
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': ['confs']}},
    )
    return config


def new_csv_with_multiple_displays_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'default': 'Unknown', 'field': 'firstname'},
            {'title': 'Lastname', 'default': 'Unknown', 'field': 'lastname'},
            {'title': 'Number', 'default': '', 'field': 'number'},
            {'field': 'favorite', 'type': 'favorite'},
        ],
    )
    config.with_display(
        name='second_display',
        columns=[
            {
                'title': 'fn',
                'default': 'Unknown',
                'field': 'firstname',
                'type': 'firstname',
            },
            {'title': 'ln', 'default': 'Unknown', 'field': 'lastname'},
            {'title': 'Empty', 'field': 'not_there'},
            {'type': 'status'},
            {'title': 'Default', 'default': 'Default'},
        ],
    )
    config.with_source(
        backend='csv',
        name='my_csv',
        file='/tmp/data/test.csv',
        separator=",",
        unique_column='id',
        searched_columns=['fn', 'ln'],
        first_matched_columns=['num'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'email': "{eml}",
            'number': "{num}",
            'reverse': '{fn} {ln}',
        },
    )
    config.with_source(
        backend='csv',
        name='my_csv_no_email',
        file='/tmp/data/test_no_email.csv',
        separator=",",
        unique_column='id',
        searched_columns=['fn', 'ln'],
        first_matched_columns=['num'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'number': "{num}",
            'reverse': '{fn} {ln}',
        },
    )
    config.with_source(
        backend='csv',
        tenant_uuid=TENANT_UUID_2,
        name='my_csv_2',
        file='/tmp/data/test.csv',
        separator=",",
        unique_column='id',
        searched_columns=['fn', 'ln'],
        first_matched_columns=['num'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'email': "{eml}",
            'number': "{num}",
            'reverse': '{fn} {ln}',
        },
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['my_csv', 'my_csv_no_email'], 'timeout': 0.5},
            'favorites': {'sources': ['my_csv', 'my_csv_no_email'], 'timeout': 0.5},
            'reverse': {'sources': ['my_csv', 'my_csv_no_email'], 'timeout': 0.5},
        },
    )
    config.with_profile(
        name='test',
        display='second_display',
        services={
            'lookup': {'sources': ['my_csv']},
            'favorites': {'sources': ['my_csv']},
        },
    )
    return config


def new_csv_with_pipes_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='csv',
        name='my_csv',
        file='/tmp/data/test.csv',
        separator="|",
        searched_columns=['fn', 'ln'],
        format_columns={'lastname': "{ln}", 'firstname': "{fn}", 'number': "{num}"},
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': ['my_csv']}},
    )
    return config


def new_half_broken_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {
                'sources': ['my_csv', 'broken', 'my_other_csv'],
                'timeout': 0.5,
            },
            'reverse': {
                'sources': ['chained_broken_first_lookup', 'chained_second_lookup']
            },
            'favorites': {'sources': ['my_csv', 'broken', 'my_other_csv']},
        },
    )
    config.with_source(
        backend='csv',
        name='my_csv',
        file='/tmp/data/test.csv',
        separator="|",
        unique_column='id',
        searched_columns=['fn', 'ln'],
        format_columns={'lastname': "{ln}", 'firstname': "{fn}", 'number': "{num}"},
    )
    config.with_source(
        backend='csv',
        name='my_other_csv',
        file='/tmp/data/test.csv',
        separator="|",
        searched_columns=['fn', 'ln'],
        format_columns={'lastname': "{ln}", 'firstname': "{fn}", 'number': "{num}"},
    )
    config.with_source(backend='broken', name='broken')
    config.with_source(
        backend='chained_broken_first_lookup', name='chained_broken_first_lookup'
    )
    config.with_source(backend='chained_second_lookup', name='chained_second_lookup')
    return config


def new_ldap_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='ldap',
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        },
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['test_ldap']},
            'reverse': {'sources': ['test_ldap']},
            'favorites': {'sources': ['test_ldap']},
        },
    )
    return config


def new_ldap_city_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='ldap',
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        ldap_custom_filter='(l=Québec)',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        },
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': ['test_ldap']}},
    )
    return config


def new_ldap_service_down_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='ldap',
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        },
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': ['test_ldap']}},
    )
    return config


def new_ldap_service_innactive_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='ldap',
        name='test_ldap',
        ldap_uri='ldap://slapd',
        ldap_base_dn='ou=québec,dc=wazo-dird,dc=wazo,dc=community',
        ldap_username='cn=admin,dc=wazo-dird,dc=wazo,dc=community',
        ldap_password='wazopassword',
        unique_column='entryUUID',
        searched_columns=['cn', 'telephoneNumber'],
        first_matched_columns=['telephoneNumber'],
        format_columns={
            'firstname': "{givenName}",
            'lastname': "{sn}",
            'number': "{telephoneNumber}",
            'reverse': "{cn}",
        },
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={'lookup': {'sources': ['test_ldap']}},
    )
    return config


def new_multiple_sources_config(Session):
    config = Config(Session)
    config.with_display(**DEFAULT_DISPLAY)
    config.with_source(
        backend='csv',
        name='my_csv',
        file='/tmp/data/test.csv',
        separator=',',
        searched_columns=['ln', 'fn'],
        first_matched_columns=['num'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'number': "{num}",
            'reverse': "{fn} {ln}",
        },
    )
    config.with_source(
        backend='csv',
        name='second_csv',
        file='/tmp/data/test.csv',
        separator=',',
        searched_columns=['ln'],
        first_matched_columns=['num'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'number': "{num}",
            'reverse': "{fn} {ln}",
        },
    )
    config.with_source(
        backend='csv',
        name='third_csv',
        file='/tmp/data/other.csv',
        unique_column='clientno',
        separator=',',
        searched_columns=['firstname', 'lastname', 'number'],
        first_matched_columns=['number', 'mobile'],
        format_columns={'reverse': "{firstname} {lastname}"},
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['my_csv', 'second_csv', 'third_csv']},
            'reverse': {'sources': ['my_csv', 'second_csv', 'third_csv']},
        },
    )
    return config


def new_null_config(Session):
    config = Config(Session)
    return config


def new_personal_only_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {
                'title': 'Number',
                'field': 'number',
                'number_display': '{firstname} {lastname}',
            },
            {'title': 'Favorite', 'type': 'favorite'},
        ],
    )
    config.with_source(
        backend='personal',
        name='personal',
        db_uri='postgresql://asterisk:proformatique@db/asterisk',
        searched_columns=['firstname', 'lastname'],
        first_matched_columns=['number'],
        format_columns={'reverse': '{firstname} {lastname}'},
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['personal']},
            'reverse': {'sources': ['personal']},
            'favorites': {'sources': ['personal']},
        },
    )

    return config


def new_phone_config(Session):
    config = Config(Session)
    config.with_display(
        name='default',
        columns=[
            {'field': 'phone', 'type': 'number', 'number_display': '{display_name}'}
        ],
    )
    config.with_display(
        name='test_fallback',
        columns=[
            {'field': 'phone', 'type': 'number', 'number_display': '{display_name}'},
            {'field': 'phone1', 'type': 'number', 'number_display': '{display_name1}'},
        ],
    )
    config.with_source(
        backend='csv',
        name='test_sorted',
        file='/tmp/data/test_sorted.csv',
        searched_columns=['fn'],
        format_columns={'display_name': "{fn}", 'phone': "{num}"},
    )
    config.with_source(
        backend='csv',
        name='test_fallback',
        file='/tmp/data/test_fallback.csv',
        searched_columns=['fn', 'fn1'],
        format_columns={
            'display_name': "{fn}",
            'display_name1': "{fn1}",
            'phone': "{num}",
            'phone1': "{num1}",
        },
    )
    config.with_profile(
        name='test_fallback',
        display='test_fallback',
        services={'lookup': {'sources': ['test_fallback']}},
    )
    config.with_profile(
        name='test_sorted',
        display='default',
        services={'lookup': {'sources': ['test_sorted']}},
    )
    return config


def new_phone_view_config(Session):
    config = Config(Session)
    config.with_display(
        name='default',
        columns=[
            {'field': 'phone', 'type': 'number', 'number_display': '{display_name}'}
        ],
    )
    config.with_source(
        backend='csv',
        name='test_csv',
        file='/tmp/data/test.csv',
        searched_columns=['ln', 'fn'],
        format_columns={
            'lastname': "{ln}",
            'firstname': "{fn}",
            'display_name': "{fn} {ln}",
            'phone': "{num}",
        },
    )
    config.with_profile(
        name='default',
        display='default',
        services={'lookup': {'sources': ['test_csv']}},
    )
    return config


def new_wazo_users_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'default': '', 'field': 'exten'},
            {'title': 'Mobile', 'default': '', 'field': 'mobile_phone_number'},
        ],
    )
    config.with_source(
        backend='wazo',
        name='wazo_america',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
        first_matched_columns=['exten'],
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['wazo_america']},
            'reverse': {'sources': ['wazo_america']},
        },
    )
    return config


def new_wazo_users_multiple_wazo_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'exten'},
        ],
    )
    config.with_source(
        backend='wazo',
        name='wazo_asia',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'asia', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_source(
        backend='wazo',
        name='wazo_america',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_source(
        backend='wazo',
        name='wazo_europe',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'europe', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_source(
        tenant_uuid=SUB_TENANT,
        backend='wazo',
        name='wazo_america_sub',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_profile(
        name='default',
        display='default_display',
        services={
            'lookup': {'sources': ['wazo_america', 'wazo_asia', 'wazo_europe']},
            'favorites': {'sources': ['wazo_america', 'wazo_asia', 'wazo_europe']},
        },
    )
    return config


def new_multi_source_profile(Session):
    config = Config(Session)
    config.with_display(
        name='main_display',
        tenant_uuid=MAIN_TENANT,
        columns=[{'title': 'Firstname', 'field': 'firstname'}],
    )
    config.with_display(
        name='sub_display',
        tenant_uuid=SUB_TENANT,
        columns=[{'title': 'Firstname', 'field': 'firstname'}],
    )
    config.with_source(
        backend='csv', tenant_uuid=MAIN_TENANT, name='csv_main', file='/tmp/test.csv'
    )
    config.with_source(
        backend='csv', tenant_uuid=SUB_TENANT, name='csv_sub', file='/tmp/test.csv'
    )
    config.with_source(
        backend='personal',
        tenant_uuid=MAIN_TENANT,
        name='personal_main',
        db_uri='db_uri',
    )
    config.with_source(
        backend='personal', tenant_uuid=SUB_TENANT, name='personal_sub', db_uri='db_uri'
    )
    config.with_source(
        backend='wazo',
        name='a_wazo_main',
        tenant_uuid=MAIN_TENANT,
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'asia', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_source(
        backend='wazo',
        tenant_uuid=SUB_TENANT,
        name='wazo_sub',
        auth={
            'host': 'auth',
            'username': 'foo',
            'password': 'bar',
            'prefix': None,
            'https': False,
        },
        confd={'host': 'america', 'port': 9486, 'https': False, 'prefix': None},
        searched_columns=['firstname', 'lastname'],
    )
    config.with_profile(
        name='main',
        tenant_uuid=MAIN_TENANT,
        display='main_display',
        services={
            'lookup': {'sources': ['a_wazo_main', 'personal_main']},
            'favorites': {'sources': ['a_wazo_main', 'personal_main']},
            'reverse': {'sources': ['csv_main', 'personal_main']},
        },
    )
    config.with_profile(
        name='sub',
        tenant_uuid=SUB_TENANT,
        display='sub_display',
        services={
            'lookup': {'sources': ['wazo_sub', 'personal_sub']},
            'favorites': {'sources': ['wazo_sub', 'personal_sub']},
            'reverse': {'sources': ['csv_sub', 'personal_sub']},
        },
    )
    return config
