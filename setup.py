#!/usr/bin/env python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'megairc',
    version     = '0.0.1',
    packages    = ['megairc'],
    author      = 'luk3yx',
    description = 'WIP',
    url         = 'https://github.com/luk3yx/megairc',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['miniirc'],
    python_requires               = '>=3.5',

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)
