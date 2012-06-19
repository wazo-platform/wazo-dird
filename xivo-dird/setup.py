#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from distutils.core import setup

setup(
    name='xivo-dird',
    version='1.2',
    description='XiVO Directory Daemon',
    author='Avencall',
    author_email='dev@avencall.com',
    url='http://git.xivo.fr/',
    packages=['xivo_dird',
              'xivo_dird.bin',
              'xivo_dird.agi',
             ],
    scripts=['bin/xivo-dird'],
)
