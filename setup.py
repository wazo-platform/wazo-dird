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
    packages=[
        'xivo_dird',
        'xivo_dird.directory',
        'xivo_dird.directory.data_sources',
    ],
)
