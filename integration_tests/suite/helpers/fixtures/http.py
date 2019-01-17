# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import requests
from functools import wraps


def wazo_source(**source_args):
    source_args.setdefault('auth', {'key_file': '/path/to/key/file'})
    source_args.setdefault('token', 'valid-token-master-tenant')

    def decorator(decorated):

        @wraps(decorated)
        def wrapper(self, *args, **kwargs):
            client = self.get_client(source_args['token'])
            source = client.wazo_source.create(source_args)
            try:
                result = decorated(self, source, *args, **kwargs)
            finally:
                try:
                    self.client.wazo_source.delete(source['uuid'])
                except requests.HTTPError as e:
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None)
                    if status_code != 404:
                        raise
            return result
        return wrapper
    return decorator
