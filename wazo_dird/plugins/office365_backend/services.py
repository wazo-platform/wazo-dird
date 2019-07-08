# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import uuid

import requests

from wazo_auth_client import Client as Auth

from .exceptions import MicrosoftTokenNotFoundException, UnexpectedEndpointException


logger = logging.getLogger(__name__)


class Office365Service:

    USER_AGENT = 'wazo_ua/1.0'

    def get_contacts_with_term(self, microsoft_token, term, url):
        headers = self.headers(microsoft_token)
        query_params = {
            "search": term
        }
        try:
            response = requests.get(url, headers=headers, params=query_params)
            if response.status_code == 200:
                logger.debug('Sucessfully fetched contacts from microsoft.')
                return response.json().get('value', [])
            else:
                return []
        except requests.exceptions.RequestException as e:
            logger.error('Unable to get contacts from this endpoint: %s, error : %s', url, e)
            return []

    def get_contacts(self, microsoft_token, url):
        headers = self.headers(microsoft_token)
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                logger.debug('Successfully fetched contacts from microsoft.')
                return response.json().get('value', [])
            else:
                logger.error('An error occured while fetching information from microsoft endpoint')
                raise UnexpectedEndpointException(endpoint=url, error_code=response.status_code)
        except requests.exceptions.RequestException:
            raise UnexpectedEndpointException(endpoint=url)

    def headers(self, microsoft_token):
        return {
            'User-Agent': self.USER_AGENT,
            'Authorization': 'Bearer {0}'.format(microsoft_token),
            'Accept': 'application/json',
            'client-request-id': str(uuid.uuid4),
            'return-client-request-id': 'true'
        }


def get_microsoft_access_token(user_uuid, wazo_token, **auth_config):
    try:
        auth = Auth(token=wazo_token, **auth_config)
        return auth.external.get('microsoft', user_uuid).get('access_token')
    except requests.HTTPError as e:
        logger.error('Microsoft token could not be fetched from wazo-auth, error %s', e)
        raise MicrosoftTokenNotFoundException(user_uuid)
    except requests.exceptions.ConnectionError as e:
        logger.error('Unable to connect auth-client for the given parameters: %s, error :%s.', auth_config, e)
        raise MicrosoftTokenNotFoundException(user_uuid)
    except requests.exceptions.RequestException as e:
        logger.error('Error occured while connecting to wazo-auth, error :%s', e)


def get_first_email(contact_information):
    return next(iter(contact_information.get('emailAddresses') or []), {}).get('address')
