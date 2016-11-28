#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages

setup(
    name='xivo-dird-broken-plugins',
    version='1.0',

    description='XiVO Directory Daemon broken plugins',

    author='Avencall',
    author_email='dev+pkg@proformatique.com',

    url='https://github.com/wazo-pbx/xivo-dird',

    packages=find_packages(),

    entry_points={
        'xivo_dird.backends': [
            'broken = xivo_dird_broken_plugins.broken_backend:BrokenPlugin',
            'broken_lookup = xivo_dird_broken_plugins.broken_backend:BrokenLookup',
        ],
    }
)
