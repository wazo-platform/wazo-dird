# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Avencall
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

from __future__ import unicode_literals

import sys

from flask import Flask, request, Response


app = Flask(__name__)

headers = ['id', 'firstname', 'lastname', 'number']
entries = [
    (1, 'Andrée-Anne', 'Smith', '5551231111'),
    (42, 'Benoît', 'Malone', '5551232222'),
    (3, 'Jack', 'Sparrow', '5551233333'),
]

separator = sys.argv[1]
charset = sys.argv[2]


def line(fields, separator=separator):
    return '{}\n'.format(separator.join(map(unicode, fields))).encode(charset)


@app.route('/ws')
def ws():
    result = set()

    if not request.args.keys():
        result = entries

    for field, term in request.args.iteritems():
        if field not in headers:
            continue

        i = headers.index(field)
        for entry in entries:
            if term.lower() in entry[i].lower():
                result.add(entry)

    data = list(result)
    if not data:
        return '', 404

    def generate():
        yield line(headers)
        for entry in data:
            yield line(entry)

    return Response(generate(), content_type='text/csv; charset={}'.format(charset))


def main():
    app.run(host='0.0.0.0', port=9485)


if __name__ == '__main__':
    main()
