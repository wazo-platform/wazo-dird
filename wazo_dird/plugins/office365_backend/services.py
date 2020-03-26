# Copyright 2019-2020 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import uuid

import requests

from operator import itemgetter
from wazo_auth_client import Client as Auth

from .exceptions import MicrosoftTokenNotFoundException, UnexpectedEndpointException


logger = logging.getLogger(__name__)

NUMBER_FIELDS = ('businessPhones', 'homePhones', 'mobilePhone')


class Office365Service:

    USER_AGENT = 'wazo_ua/1.0'

    def get_contacts(self, microsoft_token, url, **list_params):
        count = self._get_total_contacts(microsoft_token, url)
        contacts = list(self._fetch(microsoft_token, url, count))
        total_contacts = len(contacts)
        sorted_contacts = self._sort(contacts, **list_params)
        paginated_contacts = self._paginate(sorted_contacts, **list_params)
        return paginated_contacts, total_contacts

    def _fetch(self, microsoft_token, url, count):
        headers = self.headers(microsoft_token)
        try:
            response = requests.get(url, headers=headers, params={'$top': count})
            if response.status_code == 200:
                logger.debug('Successfully fetched contacts from microsoft.')
                return response.json().get('value', [])
            else:
                logger.error(
                    'An error occured while fetching information from microsoft endpoint'
                )
                raise UnexpectedEndpointException(
                    endpoint=url, error_code=response.status_code
                )
        except requests.RequestException:
            raise UnexpectedEndpointException(endpoint=url)

    def _get_total_contacts(self, microsoft_token, url):
        headers = self.headers(microsoft_token)
        try:
            response = requests.get(url, headers=headers, params={'$count': 'true'})
            if response.status_code == 200:
                count = response.json().get('@odata.count', 0)
                logger.debug(
                    'Successfully got contact number from Microsoft: %s', count
                )
                return count
            else:
                logger.error(
                    'An error occured while fetching information from Microsoft endpoint'
                )
                raise UnexpectedEndpointException(
                    endpoint=url, error_code=response.status_code
                )
        except requests.RequestException:
            raise UnexpectedEndpointException(endpoint=url)

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

    def _sort(self, contacts, order=None, direction=None, **_):
        if not order:
            return contacts

        reverse = direction == 'desc'
        return sorted(contacts, key=itemgetter(order), reverse=reverse)

    def headers(self, microsoft_token):
        return {
            'User-Agent': self.USER_AGENT,
            'Authorization': 'Bearer {0}'.format(microsoft_token),
            'Accept': 'application/json',
            'client-request-id': str(uuid.uuid4),
            'return-client-request-id': 'true',
        }


def get_microsoft_access_token(user_uuid, wazo_token, **auth_config):
    try:
        auth = Auth(token=wazo_token, **auth_config)
        return auth.external.get('microsoft', user_uuid).get('access_token')
    except requests.HTTPError as e:
        logger.error('Microsoft token could not be fetched from wazo-auth, error %s', e)
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
    for field in NUMBER_FIELDS:
        field_value = contact.get(field)
        if field_value:
            if isinstance(field_value, list):
                all_numbers.extend(field_value)
            else:
                all_numbers.append(field_value)
    return all_numbers
