#!/usr/bin/env python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc_extras',
    version     = '0.2.6',
    packages    = ['miniirc_extras', 'miniirc_extras.features'],
    author      = 'luk3yx',
    description = 'WIP extensions for miniirc.',
    url         = 'https://github.com/luk3yx/miniirc_extras',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['miniirc>=1.4.0', 'deprecated>=1.2.5,<2'],
    python_requires               = '>=3.5',

    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
    ]
)
