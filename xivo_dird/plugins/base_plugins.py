# -*- coding: utf-8 -*-
#
# Copyright (C) 2014-2015 Avencall
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


class BaseServicePlugin(object):
    '''
    This is the base class of a dird service. The service is responsible of
    its directory sources
    '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self, args):
        '''
        Bootstraps the plugin instance. The flask app, bus connection and other
        handles will be passed through the args dictionary
        '''

    def unload(self):
        '''
        Does the cleanup before the service can be deleted
        '''


class BaseViewPlugin(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self, args):
        '''
        The load method is responsible of acquiring resources for the plugin and
        add the routes to the http_app.
        '''


class BaseSourcePlugin(object):
    '''
    A backend plugin in xivo should implement this base class implicitly or
    explicitly
    '''

    __metaclass__ = abc.ABCMeta

    # These string are expected in the configuration
    SEARCHED_COLUMNS = 'searched_columns'  # These columns are the ones we search in
    FORMAT_COLUMNS = 'format_columns'
    UNIQUE_COLUMN = 'unique_column'  # This is the column that make an entry unique

    @abc.abstractmethod
    def load(self, args):
        '''
        The load function is responsible for setting up the source and acquiring
        any resources necessary.
        '''

    def unload(self):
        '''
        The unload method is used to release any resources that are under the
        responsibility of this instance.
        '''

    @abc.abstractmethod
    def search(self, term, args=None):
        '''
        The search method should return a list of dict containing the search
        results.

        The results should include the columns that are expected by the display.
        When columns from the source do not match the columns from the display,
        the `format_columns` dictionary can be used by the administrator
        to add or modify columns.

        If the backend has a `unique_column` configuration, a new column will be
        added with a `__unique_id` header containing the unique key.
        '''

    def list(self, uids, args):
        '''
        Returns a list of results based on the unique column for this backend.
        This function is not mandatory as some backends make it harder than
        others to query for specific ids. If a backend does not provide the list
        function, it will not be possible to set a favourite from this backend.

        Results returned from list should be formatted in the same way than
        results from search. Meaning that the `__unique_id` column should be
        added and display columns should be present.
        '''
        return []
