# -*- coding: utf-8 -*-
# Copyright (C) 2015-2016 Avencall
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import unicode_literals

import sys

from flask import Flask, request, Response


app = Flask(__name__)

context = ('/usr/local/share/ssl/dird/server.crt', '/usr/local/share/ssl/dird/server.key')

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
    app.run(host='0.0.0.0', port=9485, ssl_context=context)


if __name__ == '__main__':
    main()
