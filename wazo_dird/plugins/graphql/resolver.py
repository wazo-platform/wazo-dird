# Copyright 2020-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from flask import request
from wazo_dird import auth
from wazo_dird.exception import NoSuchProfile, NoSuchProfileAPIException

from . import schema
from .exceptions import graphql_error_from_api_exception


class Resolver:
    def __init__(self, profile_service, reverse_service):
        self.profile_service = profile_service
        self.reverse_service = reverse_service

    def hello(self, root, info, **args):
        return 'world'

    def get_user_me(self, root, info, **args):
        token = request.headers['X-Auth-Token']
        token_info = auth.client().token.get(token)
        metadata = token_info['metadata']
        info.context['token_id'] = token
        info.context['user_uuid'] = metadata['uuid']
        info.context['tenant_uuid'] = metadata['tenant_uuid']
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
            return self.reverse_service.reverse_many(
                profile_config,
                args['extens'],
                profile,
                user_uuid=user_uuid,
                token=token_id,
            )
        return []

    def get_contact_type(self, contact, info):
        if contact.backend == 'wazo':
            return schema.WazoContact
        return schema.Contact

    def get_contact_field(self, contact, info, **args):
        return contact.fields.get(info.field_name)

    def get_contact_user_uuid(self, contact, info, **args):
        return contact.relations['user_uuid']

    def get_reverse_field(self, contact, info, **args):
        return contact.fields['reverse']

    def get_source_entry_id(self, contact, info, **args):
        return None if contact.source_entry_id is None else contact.source_entry_id()

    def get_source_name(self, contact, info, **args):
        return contact.source

    def get_backend(self, contact, info, **args):
        return contact.backend
