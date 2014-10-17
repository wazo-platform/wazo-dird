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
        results

        If the backend has a unique column, the columns will be added with a
        `__unique_id` header
        '''

    def list(self, uids):
        '''
        Returns a list of results based on the unique column for this backend.
        This function is not mandatory as some backends make it harder that other
        to query for specific ids. If a backend does not profide the list
        function, it will not be possible to set a favorite from this backend.
        '''
        return []
