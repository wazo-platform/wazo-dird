#!/usr/bin/env python
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

old_name = 'source_to_display_columns'
new_name = 'format_columns'

def is_first_level(line):
    return not line.startswith(' ')


def is_section_start(line):
    return line.startswith(old_name)


def main(filename):
    print 'Updating xivo-dird source configuration file: {}'.format(filename)
    try:
        content = get_modified_content(filename)
        write_modified_content(filename, content)
    except Exception:
        print >> sys.stderr, 'Failed to migrate xivo-dird configuration file {}'.format(filename)
    

def get_modified_content(filename):
    in_section = False
    content = []

    for line in open(filename, 'r'):
        if is_first_level(line):
            if is_section_start(line):
                in_section = True
                content.append(line.replace(old_name, new_name))
            else:
                in_section = False
                content.append(line)
        elif in_section:
            kv, _, comment = line.partition('#')
            key, _, value = kv.partition(':')
            leading_spaces = key.rfind(' ')
            if comment:
                comment = '# {}'.format(comment)

            new_line = ' ' * leading_spaces + value.rstrip() + ': "{' + key.strip() + '}" ' + comment
            content.append(new_line.rstrip() + '\n')
        else:
            content.append(line)

    return content

def write_modified_content(filename, content):
    with open(filename, 'w') as f:
        for line in content:
            f.write(line)


if __name__ == '__main__':
    main(sys.argv[1])
