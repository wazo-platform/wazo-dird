# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import uuid
import random
import string

from functools import wraps

from wazo_dird import exception


def _new_uuid():
    return str(uuid.uuid4())


def _random_string(n):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(n))


def display(**display_args):
    display_args.setdefault('name', _random_string(16))
    display_args.setdefault('tenant_uuid', _new_uuid())
    display_args.setdefault('columns', [])

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            display = self.display_crud.create(**display_args)
            try:
                result = decorated(self, display, *args, **kwargs)
            finally:
                try:
                    self.display_crud.delete(None, display['uuid'])
                except exception.NoSuchDisplay:
                    pass
            return result
        return wrapper
    return decorator


def profile(**profile_args):
    profile_args.setdefault('name', _random_string(10))
    profile_args.setdefault('tenant_uuid', _new_uuid())
    profile_args.setdefault('services', {})
    profile_args.setdefault('display', None)

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            profile = self.profile_crud.create(profile_args)
            try:
                result = decorated(self, profile, *args, **kwargs)
            finally:
                try:
                    self.profile_crud.delete(None, profile['uuid'])
                except exception.NoSuchProfile:
                    pass
            return result
        return wrapper
    return decorator


def source(**source_args):
    source_args.setdefault('backend', 'csv')
    source_args.setdefault('tenant_uuid', _new_uuid())
    source_args.setdefault('name', _random_string(10))
    source_args.setdefault('searched_columns', [])
    source_args.setdefault('first_matched_columns', [])
    source_args.setdefault('format_columns', {})
    backend = source_args.pop('backend')

    def decorator(decorated):
        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            source = self.source_crud.create(backend, source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.source_crud.delete(backend, source['uuid'], visible_tenants=None)
                except exception.NoSuchSource:
                    pass
            return result
        return wrapper
    return decorator
