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
