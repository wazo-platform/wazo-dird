#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name='wazo-dird-broken-plugins',
    version='1.0',
    description='Wazo Directory Daemon broken plugins',
    author='The Wazo Authors',
    author_email='dev+pkg@wazo.community',
    url='https://github.com/wazo-platform/wazo-dird',
    packages=find_packages(),
    entry_points={
        'wazo_dird.backends': [
            'broken = xivo_dird_broken_plugins.broken_backend:BrokenPlugin',
            'broken_lookup = xivo_dird_broken_plugins.broken_backend:BrokenLookup',
            'chained_broken_first_lookup = xivo_dird_broken_plugins.broken_backend:ChainedBrokenFirstLookup',
            'chained_second_lookup = xivo_dird_broken_plugins.broken_backend:ChainedSecondLookup',
        ],
        'wazo_dird.services': [
            'broken_bus = xivo_dird_broken_plugins.broken_service:BrokenBusPlugin',
        ],
    },
)
