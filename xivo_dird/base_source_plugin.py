# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import abc


class BaseSourcePlugin(object):
    '''
    A backend plugin in xivo should implement this base class implicitly or
    explicitly
    '''

    __metaclass__ = abc.ABCMeta

    # These string are expected in the configuration
    SEARCHED_COLUMNS = 'searched_columns'  # These columns are the ones we search in
    UNIQUE_COLUMNS = 'unique_columns'  # These are the columns that make an entry unique

    # This is the column header of the unique id of a given result
    UNIQUE_COLUMN_HEADER = '__unique_id'

    @abc.abstractmethod
    def search(self, *args, **kwargs):
        '''
        The search method should return a list of dict containaing the search
        results.

        The results should include the columns that are exepcted by the display.
        When columns from the source do not match the columns from the display,
        the `source_to_display_columns` dictionary can be used by the administrator
        to add new mapping.

        If the backend has a `unique_columns` configuration, a new column will be
        added with a `__unique_id` header containing the unique key.
        '''

    def list(self, uids):
        '''
        Returns a list of results based on the unique column for this backend.
        This function is not mandatory as some backends make it harder than
        others to query for specific ids. If a backend does not provide the list
        function, it will not be possible to set a favorite from this backend.

        Results returned from list should be formatted in the same way than
        results from search. Meaning that the `__unique_id` column should be
        added and display columns should be present.
        '''
        return []
