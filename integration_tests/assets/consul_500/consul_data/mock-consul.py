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

import logging
import sys

from flask import Flask

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

port = int(sys.argv[1])


@app.route("/<path:path>", methods=['GET', 'PUT', 'DELETE'], strict_slashes=False)
def error_500(path):
    return 'Internal Consul error', 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port, debug=True)
