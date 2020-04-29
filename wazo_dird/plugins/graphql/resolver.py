# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from wazo_dird import auth


class Resolver:
    def hello(self, root, info, **args):
        return 'world'

    def get_user_me(self, root, info, **args):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        info.context['current_token_id'] = token
        info.context['current_user_uuid'] = token_infos['metadata']['uuid']
        return {}

    def get_user_me_uuid(self, root, info, **args):
        return info.context['current_user_uuid']

    def get_user_contacts(self, root, info, **args):
        return [{}, {}]

    def get_contact_firstname(self, root, info, **args):
        return 'paul'
