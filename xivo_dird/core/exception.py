# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Avencall
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


class ProfileNotFoundError(Exception):

    pass


class InvalidConfigError(Exception):

    def __init__(self, location_path, msg):
        super(InvalidConfigError, self).__init__(location_path, msg)
        self.location_path = location_path
        self.msg = msg


class InvalidPhonebookException(Exception):

    def __init__(self, errors):
        self.errors = errors
