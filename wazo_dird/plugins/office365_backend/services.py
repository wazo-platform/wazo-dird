# Copyright 2019-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import itertools
import logging
import uuid

import requests

from wazo_auth_client import Client as Auth

from wazo_dird.plugin_helpers.self_sorting_service import SelfSortingServiceMixin

from .exceptions import MicrosoftTokenNotFoundException, UnexpectedEndpointException


logger = logging.getLogger(__name__)

MULTI_PHONE_FIELDS = ('businessPhones', 'homePhones')
SINGLE_PHONE_FIELDS = ('mobilePhone',)


class Office365Service(SelfSortingServiceMixin):
    USER_AGENT = 'wazo_ua/1.0'

    def get_contacts(self, microsoft_token, url, **list_params):
        count = self._get_total_contacts(microsoft_token, url)
        contacts = list(self._fetch(microsoft_token, url, count))
        total_contacts = len(contacts)
        sorted_contacts = self.sort(contacts, **list_params)
        paginated_contacts = self._paginate(sorted_contacts, **list_params)
        return paginated_contacts, total_contacts

    def _fetch(self, microsoft_token, url, count):
        if not count:
            return []

        headers = self.headers(microsoft_token)
        response = self._get_data(url, headers, {'$top': count})
        contacts = self._extract_contacts(response)

        while '@odata.nextLink' in response.json():
            logger.debug('Moving to the next page...')
            next_page_url = response.json().get('@odata.nextLink')
            response = self._get_data(next_page_url, headers)
            contacts += self._extract_contacts(response)

        return contacts

    def _get_data(self, url, headers, params=None):
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            logger.debug(f'Successfully fetched data from Microsoft {url}')
            return response
        else:
            logger.error(
                f'An error occured while fetching data from Microsoft {url} - ',
                response.json(),
            )
            raise UnexpectedEndpointException(
                endpoint=url, error_code=response.status_code
            )

    def _extract_contacts(self, response):
        return response.json().get('value', [])

    def _get_total_contacts(self, microsoft_token, url):
        headers = self.headers(microsoft_token)
        response = self.get_data(url, headers, {'$count': 'true'})
        count = response.json().get('@odata.count', 0)
        logger.debug(f'Microsoft contacts number: %s', count)
        return count

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

    def headers(self, microsoft_token):
        return {
            'User-Agent': self.USER_AGENT,
            'Authorization': f'Bearer {microsoft_token}',
            'Accept': 'application/json',
            'client-request-id': str(uuid.uuid4),
            'return-client-request-id': 'true',
        }


def get_microsoft_access_token(user_uuid, wazo_token, **auth_config):
    try:
        auth = Auth(token=wazo_token, **auth_config)
        return auth.external.get('microsoft', user_uuid).get('access_token')
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            if 'unknown-external-auth-type' in e.response.text:
                logger.debug(
                    'The "microsoft" authentication type has not been configured'
                )
                raise MicrosoftTokenNotFoundException(user_uuid)
            elif 'unknown-external-auth' in e.response.text:
                logger.debug(
                    'user %s has no "microsoft" authentication configured', user_uuid
                )
                raise MicrosoftTokenNotFoundException(user_uuid)

        logger.error(
            'Microsoft token could not be fetched from wazo-auth, error: %s', e
        )
        raise MicrosoftTokenNotFoundException(user_uuid)
    except requests.exceptions.ConnectionError as e:
        logger.error(
            'Unable to connect auth-client for the given parameters: %s, error :%s.',
            auth_config,
            e,
        )
        raise MicrosoftTokenNotFoundException(user_uuid)
    except requests.RequestException as e:
        logger.error('Error occured while connecting to wazo-auth, error :%s', e)


def get_first_email(contact_information):
    return next(iter(contact_information.get('emailAddresses') or []), {}).get(
        'address'
    )


def aggregate_numbers(contact):
    all_numbers = []
    for field in SINGLE_PHONE_FIELDS:
        field_value = contact.get(field)
        if field_value:
            all_numbers.append(field_value)
    for field in MULTI_PHONE_FIELDS:
        field_value = contact.get(field) or []
        all_numbers.extend(field_value)
    return all_numbers


def get_numbers_except_label(contact):
    numbers_by_phonetype = {}
    for phone_field in MULTI_PHONE_FIELDS:
        numbers_by_phonetype[phone_field] = contact.get(phone_field) or []

    for phone_field in SINGLE_PHONE_FIELDS:
        phone_number = contact.get(phone_field)
        if not phone_number:
            numbers_by_phonetype[phone_field] = []
        else:
            numbers_by_phonetype[phone_field] = [phone_number]

    numbers_except_phonetype = {}
    for phone_field in numbers_by_phonetype:
        candidates = dict(numbers_by_phonetype)
        candidates.pop(phone_field, None)
        numbers_except_phonetype[phone_field] = list(
            itertools.chain(*candidates.values())
        )

    return numbers_except_phonetype
