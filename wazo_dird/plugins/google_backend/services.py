# Copyright 2019-2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

import requests

from wazo_auth_client import Client as Auth
from wazo_dird.plugin_helpers.self_sorting_service import SelfSortingServiceMixin

from .exceptions import GoogleTokenNotFoundException


logger = logging.getLogger(__name__)


class GoogleService(SelfSortingServiceMixin):

    USER_AGENT = 'wazo_ua/1.0'
    people_url = 'https://people.googleapis.com/v1/people/me/connections'
    search_url = 'https://people.googleapis.com/v1/people:searchContacts'
    groups_url = 'https://google.com/m8/feeds/groups/default/full'

    def __init__(self):
        self.formatter = ContactFormatter()

    def get_contacts_with_term(self, google_token, term):
        for contact in self._fetch(google_token, term=term):
            yield contact

    def get_contacts(self, google_token, **list_params):
        contacts = list(self._fetch(google_token, term=list_params.get('search')))
        total = len(contacts)
        sorted_contacts = self.sort(contacts, **list_params)
        paginated_contacts = self._paginate(sorted_contacts, **list_params)
        return paginated_contacts, total

    def _fetch(self, google_token, term=None):
        url = self.people_url
        headers = self.headers(google_token)
        query_params = {
            'personFields': 'names,emailAddresses,phoneNumbers,addresses,organizations',
            'pageSize': 1000,
        }

        if term:
            url = self.search_url
            query_params = {  # personFields becomes 'readMask' when searching; both should be the same
                'readMask': 'names,emailAddresses,phoneNumbers,addresses,organizations',
                'pageSize': 30,
            }
            requests.get(
                url, headers=headers, params=query_params
            )  # empty request to 'warm' cache
            query_params['query'] = term

        response = requests.get(url, headers=headers, params=query_params)
        if response.status_code != 200:
            return []

        logger.debug('Sucessfully fetched contacts from google')
        logger.debug('Raw data: %s', response.text)

        if term:
            for contact in response.json().get('results', []):
                yield self.formatter.format(contact.get('person', {}))
        else:
            for contact in response.json().get('connections', []):
                yield self.formatter.format(contact)

    def _paginate(self, contacts, limit=None, offset=None, **_):
        if limit is None and offset is None:
            return contacts

        if offset:
            end = contacts[offset:]
        else:
            end = contacts

        if limit is None:
            return end

        return end[:limit]

    def headers(self, google_token):
        return {
            'User-Agent': self.USER_AGENT,
            'Authorization': 'Bearer {}'.format(google_token),
            'Accept': 'application/json',
            'GData-Version': '3.0',
        }


def get_google_access_token(user_uuid, wazo_token, **auth_config):
    try:
        auth = Auth(token=wazo_token, **auth_config)
        return auth.external.get('google', user_uuid).get('access_token')
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            if 'unknown-external-auth-type' in e.response.text:
                logger.debug('The "google" authentication type has not been configured')
                raise GoogleTokenNotFoundException(user_uuid)
            elif 'unknown-external-auth' in e.response.text:
                logger.debug(
                    'user %s has no "google" authentication configured', user_uuid
                )
                raise GoogleTokenNotFoundException(user_uuid)

        logger.error('Google token could not be fetched from wazo-auth, error: %s', e)
        raise GoogleTokenNotFoundException(user_uuid)
    except requests.exceptions.ConnectionError as e:
        logger.error(
            'Unable to connect auth-client for the given parameters: %s, error: %s.',
            auth_config,
            e,
        )
        raise GoogleTokenNotFoundException(user_uuid)
    except requests.RequestException as e:
        logger.error('Error occurred while connecting to wazo-auth, error: %s', e)


class ContactFormatter:

    chars_to_remove = [' ', '-', '(', ')']

    def format(self, contact):
        return {
            'id': self._extract_id(contact),
            'name': self._extract_name(contact),
            'firstname': self._extract_first_name(contact),
            'lastname': self._extract_last_name(contact),
            'numbers_by_label': self._extract_numbers_by_label(contact),
            'numbers': self._extract_numbers(contact),
            'numbers_except_label': self._extract_numbers_except_label(contact),
            'emails': self._extract_emails(contact),
            'organizations': self._extract_organizations(contact),
            'addresses': self._extract_addresses(contact),
            'note': self._extract_note(contact),
        }

    @classmethod
    def _extract_emails(cls, contact):
        emails = []
        for email in contact.get('emailAddresses', []):
            address = email.get('value')
            if not address:
                continue
            label_or_type = cls._extract_type(email) or ''
            emails.append({'address': address, 'label': label_or_type})
        return emails

    @classmethod
    def _extract_numbers(cls, contact):
        numbers_by_label = cls._extract_numbers_by_label(contact)
        numbers = []
        mobile = None

        for type_, number in numbers_by_label.items():
            if type_ == 'mobile':
                mobile = number
            else:
                numbers.append(number)

        if mobile:
            numbers.append(mobile)

        return numbers

    @staticmethod
    def _extract_id(contact):
        names = contact.get('names', [])
        if not names:
            return
        _id = names[0].get('metadata', {}).get('source', {}).get('id')
        return _id

    @classmethod
    def _extract_numbers_by_label(cls, contact):
        numbers = {}
        for number in contact.get('phoneNumbers', []):
            type_ = cls._extract_type(number)
            if not type_:
                continue

            number = number.get('value')
            if not number:
                continue

            for char in cls.chars_to_remove:
                number = number.replace(char, '')

            numbers[type_] = number

        return numbers

    @classmethod
    def _extract_numbers_except_label(cls, contact):
        numbers_by_label = cls._extract_numbers_by_label(contact)
        numbers = {}

        for type_ in (
            'home',
            'work',
            'mobile',
            'other',
            'main',
            'home_fax',
            'work_fax',
            'google_voice',
            'pager',
        ):
            candidates = dict(numbers_by_label)
            candidates.pop(type_, None)
            numbers[type_] = list(candidates.values())

        return numbers

    @classmethod
    def _find_name(cls, contact):
        for name in contact.get('names', []):
            return name
        return {}

    @classmethod
    def _extract_name(cls, contact):
        name_obj = cls._find_name(contact)
        name = name_obj.get('displayName')
        if not name:
            name = name_obj.get('unstructuredName')
        return name

    @classmethod
    def _extract_first_name(cls, contact):
        return cls._find_name(contact).get('givenName')

    @classmethod
    def _extract_last_name(cls, contact):
        return cls._find_name(contact).get('familyName')

    @classmethod
    def _extract_type(cls, entry):
        return entry.get('type')

    @classmethod
    def _extract_organizations(cls, contact):
        organizations = []
        organizations_from_contact = contact.get('organizations', [])
        for organization in organizations_from_contact:
            organization_name = organization.get('name')
            organization_title = organization.get('title')
            organizations.append(
                {'name': organization_name, 'title': organization_title}
            )

        return organizations

    @classmethod
    def _extract_addresses(cls, contact):
        addresses = []
        addresses_from_contact = contact.get('addresses', [])
        for address in addresses_from_contact:
            formatted_address = address.get('formattedValue')
            label_or_type = cls._extract_type(address) or ''
            addresses.append({'address': formatted_address, 'label': label_or_type})

        return addresses

    @classmethod
    def _extract_note(cls, contact):
        return contact.get('content', {}).get('$t', '')
