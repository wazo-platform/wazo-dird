# Copyright 2015-2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import logging
import re

from collections import namedtuple
from operator import attrgetter

logger = logging.getLogger(__name__)


def new_phone_lookup_service_from_args(dependencies):
    # dependencies is the same "dependencies" argument that is passed to the load method of view plugins
    lookup_service = dependencies['services']['lookup']
    display_service = dependencies['services']['display']
    profile_service = dependencies['services']['profile']

    return _PhoneLookupService(lookup_service, display_service, profile_service)


_PhoneFormattedResult = namedtuple('_PhoneFormattedResult', ['name', 'number'])


class _PhoneLookupService:

    def __init__(self, lookup_service, display_service, profile_service):
        self._lookup_service = lookup_service
        self._display_service = display_service
        self.profile_service = profile_service

    def lookup(
            self, profile_config, tenant_uuid, term, xivo_user_uuid, token,
            limit=None, offset=0,
    ):
        display = profile_config['display']
        formatter = _PhoneResultFormatter(display)

        lookup_results = self._lookup_service.lookup(
            profile_config,
            tenant_uuid,
            term,
            xivo_user_uuid=xivo_user_uuid,
            args={},
            token=token,
        )
        formatted_results = formatter.format_results(lookup_results)
        formatted_results.sort(key=attrgetter('name', 'number'))

        return {
            'results': formatted_results[offset:offset + limit] if limit is not None else formatted_results[offset:],
            'limit': limit,
            'offset': offset,
            'total': len(formatted_results),
            'next_offset': self._next_offset(offset, limit, len(formatted_results)),
            'previous_offset': self._previous_offset(offset, limit)
        }

    def _next_offset(self, offset, limit, results_count):
        if limit is None:
            return None

        next_offset = offset + limit
        if next_offset >= results_count:
            return None

        return next_offset

    def _previous_offset(self, offset, limit):
        if offset == 0:
            return None

        if limit is None:
            return None

        previous_offset = offset - limit
        if previous_offset < 0:
            return 0

        return previous_offset


class _PhoneResultFormatter:

    _INVALID_CHARACTERS_REGEX = re.compile(r'[^\d*#+\(\)]+')
    _SPECIAL_NUMBER_REGEX = re.compile(r'^\+(\d+)\(\d+\)(\d+)$')
    _PARENTHESES_REGEX = re.compile(r'[\(\)]')

    def __init__(self, display):
        self._number_fields = self._extract_number_fields(display)

    def format_results(self, lookup_results):
        results = []
        for lookup_result in lookup_results:
            self._format_result(lookup_result.fields, results)
        return results

    def _format_result(self, fields, out):
        for display_name, number in self._extract_results(fields):
            number = self._normalize_number(number)
            if not number:
                continue
            out.append(_PhoneFormattedResult(display_name, number))

    def _normalize_number(self, number):
        number = self._extract_number_from_pretty_number(number)
        return number

    def _extract_results(self, fields):
        for candidate in self._number_fields:
            number = fields.get(candidate['field'])
            if not number:
                continue

            number_display = candidate.get('number_display')
            if not number_display:
                continue

            try:
                name = number_display.format(**fields)
            except KeyError:
                logger.info(
                    'phone lookup found a result be could not format a name %s %s',
                    number_display, fields,
                )
                continue

            yield name, number

    def _extract_number_from_pretty_number(self, pretty_number):
        number_with_parentheses = self._INVALID_CHARACTERS_REGEX.sub('', pretty_number)
        # Convert numbers +33(0)123456789 to 0033123456789
        number_with_parentheses = self._SPECIAL_NUMBER_REGEX.sub(r'00\1\2', number_with_parentheses)
        return self._PARENTHESES_REGEX.sub('', number_with_parentheses)

    @staticmethod
    def _extract_number_fields(display):
        if not display:
            return []

        return [
            field for field in display['columns']
            if field.get('type') == 'number' and field.get('field')
        ]
