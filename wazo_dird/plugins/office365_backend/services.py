# Copyright 2019-2022 The Wazo Authors  (see the AUTHORS file)
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
        headers = self.headers(microsoft_token)
        try:
            if count == 1:
                response = requests.get(url, headers=headers, params={'$top': count})
                if response.status_code == 200:
                    logger.debug('Successfully fetched contacts from microsoft.')
                    logger.debug('Raw data: %s', response.text)
                    return response.json().get('value', [])
                else:
                    logger.error(
                        'An error occured while fetching information from microsoft endpoint'
                    )
                    raise UnexpectedEndpointException(
                        endpoint=url, error_code=response.status_code
                    )
            elif count > 1:
                all_contacts_list = []
                first_page_response = requests.get(
                    url, headers=headers, params={'$top': count}
                )
                if first_page_response.status_code == 200:
                    logger.debug(
                        'Successfully fetched contacts from first page from microsoft.'
                    )
                    logger.debug('Moving to the next pages...')
                    all_contacts_list = first_page_response.json().get('value', [])
                    next_page_url = first_page_response.json().get('@odata.nextLink')
                    has_more_pages = True
                    while has_more_pages:
                        next_page_response = requests.get(
                            next_page_url,
                            headers=headers,
                            params={
                                '$top': count,
                            },
                        )
                        if next_page_response.status_code == 200:
                            logger.debug(
                                'Successfully fetched contacts from microsoft page: %s'
                                % next_page_url
                            )
                            all_contacts_list += next_page_response.json().get(
                                'value', []
                            )
                            if '@odata.nextLink' in next_page_response.json():
                                next_page_url = next_page_response.json().get(
                                    '@odata.nextLink'
                                )
                            else:
                                has_more_pages = False
                        else:
                            logger.error(
                                'An error occured while fetching information from microsoft endpoint: %s'
                                % next_page_url
                            )
                            raise UnexpectedEndpointException(
                                endpoint=next_page_url,
                                error_code=next_page_response.status_code,
                            )
                    return all_contacts_list
                else:
                    logger.error(
                        'An error occured while fetching information from microsoft endpoint'
                    )
                    raise UnexpectedEndpointException(
                        endpoint=url, error_code=first_page_response.status_code
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
