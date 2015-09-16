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


class PhoneDisplay(object):

    DEFAULT_DISPLAY_NAME = 'default'

    def __init__(self, displays, profile_to_display):
        self._displays = displays
        self._profile_to_display = profile_to_display

    def get_name_field(self, profile):
        display = self._get_display(profile)
        return display['name']

    def get_number_field(self, profile):
        display = self._get_display(profile)
        return display['number']

    def _get_display(self, profile):
        display_name = self._profile_to_display.get(profile)
        display = self._displays.get(display_name)
        if not display:
            display = self._displays[self.DEFAULT_DISPLAY_NAME]
        return display

    @classmethod
    def new_from_config(cls, views_config):
        displays = views_config['displays_phone']
        profile_to_display = views_config.get('profile_to_display_phone', {})
        return cls(displays, profile_to_display)
