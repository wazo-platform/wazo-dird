# -*- coding: utf-8 -*-

# Copyright (C) 2015 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import re

from collections import namedtuple
from operator import attrgetter
from xivo_dird.core.exception import InvalidConfigError

INVALID_CHARACTERS_REGEX = re.compile(r'[^\d*#+\(\)]+')
SPECIAL_NUMBER_REGEX = re.compile(r'^\+(\d+)\(\d+\)(\d+)$')
PARENTHESES_REGEX = re.compile(r'[\(\)]')


def new_phone_display_from_config(views_config):
    return _PhoneDisplay.new_from_config(views_config)


class _PhoneDisplay(object):

    def __init__(self, displays, profile_to_display):
        self._displays = displays
        self._profile_to_display = profile_to_display

    def format_results(self, profile, lookup_results):
        display = self._get_display(profile)
        return display.format_results(lookup_results)

    def get_transform_function(self, profile):
        display = self._get_display(profile)
        return display.transform_results

    def _get_display(self, profile):
        display_name = self._profile_to_display[profile]
        return self._displays[display_name]

    @classmethod
    def new_from_config(cls, views_config):
        missing = object()

        if not isinstance(views_config, dict):
            raise InvalidConfigError('views', 'expected dict: was {}'.format(views_config))

        displays_config = views_config.get('displays_phone', missing)
        if displays_config is missing:
            raise InvalidConfigError('views', 'missing "displays_phone" key')

        if not isinstance(displays_config, dict):
            raise InvalidConfigError('views/displays_phone', 'expected dict: was {}'.format(displays_config))

        displays = {}
        for display_name, display_config in displays_config.iteritems():
            displays[display_name] = _Display.new_from_config(display_config)

        profile_to_display = views_config.get('profile_to_display_phone', {})
        if not isinstance(profile_to_display, dict):
            raise InvalidConfigError('views/profile_to_display_phone',
                                     'expected dict: was {}'.format(profile_to_display))

        for profile_name, display_name in profile_to_display.iteritems():
            if not isinstance(display_name, basestring):
                raise InvalidConfigError('views/profile_to_display_phone/{}'.format(profile_name),
                                         'expected basestring: was {}'.format(basestring))

            if display_name not in displays:
                raise InvalidConfigError('views/profile_to_display_phone/{}'.format(profile_name),
                                         'undefined display {}'.format(display_name))

        return cls(displays, profile_to_display)


_DisplayResult = namedtuple('_DisplayResult', ['name', 'number'])


class _Display(object):

    def __init__(self, name_config, number_config):
        self._name_config = name_config
        self._number_config = number_config

    def format_results(self, lookup_results):
        results = []
        for lookup_result in lookup_results:
            self._format_result(lookup_result.fields, results)
        return results

    def transform_results(self, lookup_results):
        display_results = self.format_results(lookup_results)
        display_results.sort(key=attrgetter('name', 'number'))
        return display_results

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

            out.append(_DisplayResult(display_name, number))

    def _get_value_from_candidates(self, fields, candidates):
        for candidate in candidates:
            v = fields.get(candidate)
            if v:
                return v
        return None

    def _extract_number_from_pretty_number(self, pretty_number):
        number_with_parentheses = INVALID_CHARACTERS_REGEX.sub('', pretty_number)
        # Convert numbers +33(0)123456789 to 0033123456789
        number_with_parentheses = SPECIAL_NUMBER_REGEX.sub(r'00\1\2', number_with_parentheses)
        return PARENTHESES_REGEX.sub('', number_with_parentheses)

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
            if not isinstance(candidate, basestring):
                raise InvalidConfigError('views/displays_phone/name/{}'.format(i),
                                         'expected basestring: was {}'.format(candidate))

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
                if not isinstance(candidate, basestring):
                    raise InvalidConfigError('views/displays_phone/number/{}/field/{}'.format(i, j),
                                             'expected basestring: was {}'.format(candidate))

            name_format = number_config_item.get('name_format', missing)
            if name_format is not missing and not isinstance(name_format, basestring):
                raise InvalidConfigError('views/displays_phone/number/{}/name_format'.format(i),
                                         'expected basestring: was {}'.format(name_format))

        return cls(name_config, number_config)
