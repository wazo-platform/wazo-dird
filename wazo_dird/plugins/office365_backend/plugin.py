# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from operator import itemgetter

from wazo_dird import BaseSourcePlugin, make_result_class
from wazo_dird.helpers import BaseBackendView

from .http import MicrosoftItem, MicrosoftList, MicrosoftContactList
from .exceptions import MicrosoftTokenNotFoundException
from . import services

logger = logging.getLogger(__name__)


class Office365View(BaseBackendView):

    backend = 'office365'
    item_resource = MicrosoftItem
    list_resource = MicrosoftList
    contact_list_resource = MicrosoftContactList

    def load(self, dependencies):
        super().load(dependencies)
        api = dependencies['api']
        config = dependencies['config']
        auth_config = config['auth']
        source_service = dependencies['services']['source']
        args = (auth_config, config, source_service)

        api.add_resource(
            self.contact_list_resource,
            "/backends/office365/sources/<source_uuid>/contacts",
            resource_class_args=args,
        )


class Office365Plugin(BaseSourcePlugin):

    def load(self, dependencies):
        config = dependencies['config']
        self.auth = config['auth']
        self.name = config['name']
        self.endpoint = config['endpoint']
        self.office365 = services.Office365Service()

        self.unique_column = 'id'
        format_columns = dependencies['config'].get(self.FORMAT_COLUMNS, {})
        if 'reverse' not in format_columns:
            logger.info(
                'no "reverse" column has been configured on %s will use "givenName"',
                self.name
            )
            format_columns['reverse'] = '{givenName}'

        self._SourceResult = make_result_class(
            'office365',
            self.name,
            self.unique_column,
            format_columns,
        )

        self._searched_columns = config.get(self.SEARCHED_COLUMNS, [])
        if not self._searched_columns:
            logger.info(
                'no "searched_columns" configured on "%s" no results will be matched',
                self.name,
            )

        self._first_matched_columns = config.get(self.FIRST_MATCHED_COLUMNS, [])
        if not self._first_matched_columns:
            logger.info(
                'no "first_matched_columns" configured on "%s" no results will be matched',
                self.name,
            )

    def search(self, term, args=None):
        logger.debug('Searching term=%s', term)
        try:
            microsoft_token = self._get_microsoft_token(**args)
        except MicrosoftTokenNotFoundException:
            return []

        contacts = self.office365.get_contacts_with_term(microsoft_token, term, self.endpoint)
        updated_contacts = self._update_contact_fields(contacts)

        lowered_term = term.lower()

        def match_fn(contact):
            for column in self._searched_columns:
                column_value = contact.get(column) or ''
                if lowered_term in str(column_value).lower():
                    return True
            return False

        filtered_contacts = [c for c in updated_contacts if match_fn(c)]
        sorted_contacts = sorted(filtered_contacts, key=itemgetter('givenName'))

        return [self._SourceResult(c) for c in sorted_contacts]

    def list(self, unique_ids, args=None):
        try:
            microsoft_token = self._get_microsoft_token(**args)
        except MicrosoftTokenNotFoundException:
            return []

        contacts = self.office365.get_contacts(microsoft_token, self.endpoint)
        updated_contacts = self._update_contact_fields(contacts)
        filtered_contacts = [c for c in updated_contacts if c[self.unique_column] in unique_ids]

        return [self._SourceResult(contact) for contact in filtered_contacts]

    def first_match(self, term, args=None):
        if not self._first_matched_columns:
            logger.debug(
                '%s is a source for reverse lookups but the not have a "first_matched_columns"',
                self.name,
            )
            return

        try:
            microsoft_token = self._get_microsoft_token(**args)
        except MicrosoftTokenNotFoundException:
            logger.debug('could not find a matching microsoft token, aborting first_match')
            return None

        contacts = self.office365.get_contacts(microsoft_token, self.endpoint)
        updated_contacts = self._update_contact_fields(contacts)
        lowered_term = term.lower()

        for contact in updated_contacts:
            if self._first_match_predicate(lowered_term, contact):
                return self._SourceResult(contact)

    def _first_match_predicate(self, term, contact):
        for column in self._first_matched_columns:
            column_value = contact.get(column) or ''

            if isinstance(column_value, list):
                for item in column_value:
                    if term == item.lower():
                        return True
            else:
                if term == str(column_value).lower():
                    return True

        return False

    def _get_microsoft_token(self, xivo_user_uuid, token=None, **ignored):
        if not token:
            logger.debug('Unable to search through Office365 without a token.')
            raise MicrosoftTokenNotFoundException()

        return services.get_microsoft_access_token(xivo_user_uuid, token, **self.auth)

    @staticmethod
    def _update_contact_fields(contacts):
        for contact in contacts:
            contact.setdefault('givenName', '')
            contact['email'] = services.get_first_email(contact)
        return contacts
