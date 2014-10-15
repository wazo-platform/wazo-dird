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


class BaseServicePlugin(object):
    '''
    This is the base class of a dird service. The service is responsible of
    it's directory sources
    '''

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def load(self, args=None):
        '''
        Bootstraps the plugin instance the flask app, bus connection and other
        handles will be passed through the args dictionary
        '''

    @abc.abstractmethod
    def unload(self, args=None):
        '''
        Does the cleanup before the service can be deleted
        '''
