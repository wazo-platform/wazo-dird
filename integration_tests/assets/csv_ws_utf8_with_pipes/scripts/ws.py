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

import sys

from flask import Flask, request, Response


app = Flask(__name__)

headers = ['id', 'firstname', 'lastname', 'number']
entries = [
    (1, 'Alice', 'Smith', '5551231111'),
    (42, 'Bob', 'Malone', '5551232222'),
    (3, 'Jack', 'Sparrow', '5551233333'),
]

separator = sys.argv[1]


def line(fields, separator=separator):
    return '{}\n'.format(separator.join(map(str, fields)))


@app.route('/ws')
def ws():
    lookup_term = request.args.get('search')
    reverse_term = request.args.get('phonesearch')
    if lookup_term:
        term = lookup_term.lower()
        data = []
        for entry in entries:
            # if term = "alice s" it should match alice smith
            composed_field = '{} {}'.format(entry[1].lower(), entry[2].lower()).strip()
            if term in composed_field:
                data.append(entry)
    elif reverse_term:
        data = [entry for entry in entries if entry[3] == reverse_term]
    else:
        data = entries

    if not data:
        return '', 404

    def generate():
        yield line(headers)
        for entry in data:
            yield line(entry)

    return Response(generate(), mimetype='text/csv')


def main():
    app.run(host='0.0.0.0', port=8080)


if __name__ == '__main__':
    main()
