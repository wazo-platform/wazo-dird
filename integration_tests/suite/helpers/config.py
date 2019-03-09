# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import string

from wazo_dird import database

from .constants import MAIN_TENANT


def _random_string(n):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(n))


class Config:

    default_display = {
        'name': 'default_display',
        'columns': [
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'number'},
        ],
    }

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
        if not self.displays:
            self.displays.append(self.default_display)

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
            self.display_crud.delete(visible_tenants, display['uuid'])

    def _remove_profiles(self):
        for profile in self.created_profiles.values():
            visible_tenants = [profile['tenant_uuid']]
            self.profile_crud.delete(visible_tenants, profile['uuid'])

    def _remove_sources(self):
        for source in self.created_sources.values():
            visible_tenants = [source['tenant_uuid']]
            backend = source['backend']
            self.source_crud.delete(backend, source['uuid'], visible_tenants)


def new_personal_only_config(Session):
    config = Config(Session)
    config.with_display(
        name='default_display',
        columns=[
            {'title': 'Firstname', 'field': 'firstname'},
            {'title': 'Lastname', 'field': 'lastname'},
            {'title': 'Number', 'field': 'number', 'number_display': '{firstname} {lastname}'},
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
