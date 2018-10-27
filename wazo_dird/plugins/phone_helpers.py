# -*- coding: utf-8 -*-
# Copyright 2015-2018 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0+

import re

from collections import namedtuple
from operator import attrgetter
from wazo_dird.exception import InvalidConfigError, ProfileNotFoundError


def new_phone_lookup_service_from_args(args):
    # args is the same "args" argument that is passed to the load method of view plugins
    lookup_service = args['services']['lookup']
    views_config = args['config']
    formatters = _new_formatters_from_config(views_config)
    return _PhoneLookupService(lookup_service, formatters)


_PhoneFormattedResult = namedtuple('_PhoneFormattedResult', ['name', 'number'])


class _PhoneLookupService(object):

    def __init__(self, lookup_service, formatters):
        self._lookup_service = lookup_service
        self._formatters = formatters

    def lookup(self, term, profile, xivo_user_uuid, token, limit=None, offset=0):
        formatter = self._formatters.get(profile)
        if formatter is None:
            raise ProfileNotFoundError(profile)

        lookup_results = self._lookup_service.lookup(term, profile, xivo_user_uuid, {}, token)
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


class _PhoneResultFormatter(object):

    _INVALID_CHARACTERS_REGEX = re.compile(r'[^\d*#+\(\)]+')
    _SPECIAL_NUMBER_REGEX = re.compile(r'^\+(\d+)\(\d+\)(\d+)$')
    _PARENTHESES_REGEX = re.compile(r'[\(\)]')

    def __init__(self, name_config, number_config):
        self._name_config = name_config
        self._number_config = number_config

    def format_results(self, lookup_results):
        results = []
        for lookup_result in lookup_results:
            self._format_result(lookup_result.fields, results)
        return results

    def _format_result(self, fields, out):
        name = self._get_value_from_candidates(fields, self._name_config)
        if name is None:
            return

        for number_config_item in self._number_config:
            pretty_number = self._get_value_from_candidates(fields, number_config_item['field'])
            if pretty_number is None:
                continue

            number = self._extract_number_from_pretty_number(pretty_number)
            if not number:
                continue

            name_format = number_config_item.get('name_format')
            if name_format:
                display_name = name_format.format(name=name, number=number)
            else:
                display_name = name

            out.append(_PhoneFormattedResult(display_name, number))

    def _get_value_from_candidates(self, fields, candidates):
        for candidate in candidates:
            v = fields.get(candidate)
            if v:
                return v
        return None

    def _extract_number_from_pretty_number(self, pretty_number):
        number_with_parentheses = self._INVALID_CHARACTERS_REGEX.sub('', pretty_number)
        # Convert numbers +33(0)123456789 to 0033123456789
        number_with_parentheses = self._SPECIAL_NUMBER_REGEX.sub(r'00\1\2', number_with_parentheses)
        return self._PARENTHESES_REGEX.sub('', number_with_parentheses)

    @classmethod
    def new_from_config(cls, display_config):
        missing = object()

        if not isinstance(display_config, dict):
            # XXX error location path is in fact "views/displays_phone/<display_name>"... but we don't
            #     have the display_name information here...
            raise InvalidConfigError('views/displays_phone',
                                     'expected dict: was {}'.format(display_config))

        name_config = display_config.get('name', missing)
        if name_config is missing:
            raise InvalidConfigError('views/displays_phone',
                                     'missing "name" key')

        if not isinstance(name_config, list):
            raise InvalidConfigError('views/displays_phone/name',
                                     'expected list: was {}'.format(name_config))

        if not name_config:
            raise InvalidConfigError('views/displays_phone/name',
                                     'expected length > 0')

        for i, candidate in enumerate(name_config):
            if not isinstance(candidate, str):
                raise InvalidConfigError('views/displays_phone/name/{}'.format(i),
                                         'expected str: was {}'.format(candidate))

        number_config = display_config.get('number', missing)
        if number_config is missing:
            raise InvalidConfigError('views/displays_phone', 'missing "number" key')

        if not isinstance(number_config, list):
            raise InvalidConfigError('views/displays_phone/number',
                                     'expected list: was {}'.format(number_config))

        if not number_config:
            raise InvalidConfigError('views/displays_phone/number',
                                     'expected length > 0')

        for i, number_config_item in enumerate(number_config):
            if not isinstance(number_config_item, dict):
                raise InvalidConfigError('views/displays_phone/number/{}'.format(i),
                                         'expected dict: was {}'.format(number_config_item))

            field = number_config_item.get('field', missing)
            if field is missing:
                raise InvalidConfigError('views/displays_phone/number/{}'.format(i),
                                         'missing "field" key')

            if not isinstance(field, list):
                raise InvalidConfigError('views/displays_phone/number/{}/field'.format(i),
                                         'expected list: was {}'.format(field))

            if not field:
                raise InvalidConfigError('views/displays_phone/number/{}/field'.format(i),
                                         'expected length > 0')

            for j, candidate in enumerate(field):
                if not isinstance(candidate, str):
                    raise InvalidConfigError('views/displays_phone/number/{}/field/{}'.format(i, j),
                                             'expected str: was {}'.format(candidate))

            name_format = number_config_item.get('name_format', missing)
            if name_format is not missing and not isinstance(name_format, str):
                raise InvalidConfigError('views/displays_phone/number/{}/name_format'.format(i),
                                         'expected str: was {}'.format(name_format))

        return cls(name_config, number_config)


def _new_formatters_from_config(views_config):
    missing = object()

    if not isinstance(views_config, dict):
        raise InvalidConfigError('views', 'expected dict: was {}'.format(views_config))

    displays_config = views_config.get('displays_phone', missing)
    if displays_config is missing:
        raise InvalidConfigError('views', 'missing "displays_phone" key')

    if not isinstance(displays_config, dict):
        raise InvalidConfigError('views/displays_phone', 'expected dict: was {}'.format(displays_config))

    formatters_by_display_name = {}
    for display_name, display_config in displays_config.items():
        formatters_by_display_name[display_name] = _PhoneResultFormatter.new_from_config(display_config)

    profile_to_display = views_config.get('profile_to_display_phone', {})
    if not isinstance(profile_to_display, dict):
        raise InvalidConfigError('views/profile_to_display_phone',
                                 'expected dict: was {}'.format(profile_to_display))

    formatters_by_profile_name = {}
    for profile_name, display_name in profile_to_display.items():
        if not isinstance(display_name, str):
            raise InvalidConfigError('views/profile_to_display_phone/{}'.format(profile_name),
                                     'expected str: was {}'.format(display_name))

        if display_name not in formatters_by_display_name:
            raise InvalidConfigError('views/profile_to_display_phone/{}'.format(profile_name),
                                     'undefined display {}'.format(display_name))

        formatters_by_profile_name[profile_name] = formatters_by_display_name[display_name]

    return formatters_by_profile_name
