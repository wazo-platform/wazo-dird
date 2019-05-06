# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from wazo_dird import exception


class ContactLister:

    def __init__(self, client):
        self._client = client

    def list(self, *args, **kwargs):
        try:
            return self._client.users.list(*args, view='directory', **kwargs)
        except Exception as e:
            raise exception.XiVOConfdError(self._client, e)
