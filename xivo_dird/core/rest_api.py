# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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

from flask import Flask
from flask_restplus.api import Api

VERSION = 0.1


class CoreRestApi(object):

    def __init__(self, config):
        self.app = Flask('xivo_dird', static_folder=config['static_folder'])
        self.api = Api(self.app, version=VERSION, prefix='/{}'.format(VERSION))
        self.namespace = self.api.namespace('directories', description='directories operations')
