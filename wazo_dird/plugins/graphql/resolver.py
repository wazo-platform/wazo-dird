# Copyright 2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from wazo_dird import auth
from wazo_dird.exception import NoSuchProfile, NoSuchProfileAPIException

from .exceptions import graphql_error_from_api_exception


class Resolver:
    def __init__(self, profile_service, reverse_service):
        self.profile_service = profile_service
        self.reverse_service = reverse_service

    def hello(self, root, info, **args):
        return 'world'

    def get_user_me(self, root, info, **args):
        token = request.headers['X-Auth-Token']
        token_infos = auth.client().token.get(token)
        info.context['token_id'] = token
        info.context['user_uuid'] = token_infos['metadata']['uuid']
        info.context['tenant_uuid'] = token_infos['metadata']['tenant_uuid']
        return {}

    def get_user_me_uuid(self, root, info, **args):
        return info.context['user_uuid']

    def get_user_contacts(self, root, info, **args):
        user_uuid = info.context['user_uuid']
        tenant_uuid = info.context['tenant_uuid']
        token_id = info.context['token_id']
        profile = args['profile']
        try:
            profile_config = self.profile_service.get_by_name(tenant_uuid, profile)
        except NoSuchProfile as e:
            raise graphql_error_from_api_exception(NoSuchProfileAPIException(e.profile))

        if args.get('extens'):
            results = [
                self.reverse_service.reverse(
                    profile_config, exten, profile, user_uuid=user_uuid, token=token_id,
                )
                for exten in args['extens']
            ]
            return results
        return []

    def get_contact_field(self, contact, info, **args):
        return contact.fields[info.field_name]
